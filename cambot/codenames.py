import random
import re
import os
from collections import Counter
from itertools import cycle
from enum import auto
from .emojis import *
from .utils import serialize, EnumZero
from .settings import *

class Teams(EnumZero):
    RED = auto()
    BLUE = auto()
    NEUTRAL = auto()
    BOMB = auto()

class Roles(EnumZero):
    CHOOSER = auto()
    GUESSER = auto()

class Recipients(EnumZero):
    EVERYONE = auto()
    CHOOSERS = auto()

class Modes(EnumZero):
    COOPERATION = auto()
    COMPETITION = auto()

class Statuses(EnumZero):
    RED_CHOOSER = auto()
    RED_GUESSER = auto()
    BLUE_CHOOSER = auto()
    BLUE_GUESSER = auto()
    NEUTRAL_CHOOSER = auto()
    NEUTRAL_GUESSER = auto()

CYCLES = {Modes.COOPERATION: cycle([Statuses.NEUTRAL_CHOOSER, Statuses.NEUTRAL_GUESSER]),
          Modes.COMPETITION: cycle([Statuses.RED_CHOOSER, Statuses.RED_GUESSER, Statuses.BLUE_CHOOSER, Statuses.BLUE_GUESSER])}

CONFIGURATIONS = [Counter([Statuses.NEUTRAL_CHOOSER, Statuses.NEUTRAL_GUESSER]), # coop
                  Counter([Statuses.NEUTRAL_CHOOSER, Statuses.NEUTRAL_GUESSER, Statuses.NEUTRAL_GUESSER]), # coop
                  Counter([Statuses.RED_CHOOSER, Statuses.BLUE_CHOOSER, Statuses.NEUTRAL_GUESSER]),
                  Counter([Statuses.RED_CHOOSER, Statuses.RED_GUESSER, Statuses.BLUE_CHOOSER, Statuses.BLUE_GUESSER]),
                  Counter([Statuses.RED_CHOOSER, Statuses.RED_GUESSER, Statuses.BLUE_CHOOSER, Statuses.BLUE_GUESSER, Statuses.NEUTRAL_GUESSER]),
                  Counter([Statuses.RED_CHOOSER, Statuses.RED_GUESSER, Statuses.RED_GUESSER, Statuses.BLUE_CHOOSER, Statuses.BLUE_GUESSER, Statuses.BLUE_GUESSER])]

SYMBOLS = {Statuses.RED_CHOOSER: f"{REDDOT}{SPEAKING}",
           Statuses.RED_GUESSER: f"{REDDOT}{GLASS}",
           Statuses.BLUE_CHOOSER: f"{BLUEDOT}{SPEAKING}",
           Statuses.BLUE_GUESSER: f"{BLUEDOT}{GLASS}",
           Statuses.NEUTRAL_CHOOSER: f"{WHITEDOT}{SPEAKING}",
           Statuses.NEUTRAL_GUESSER: f"{WHITEDOT}{GLASS}"}

class Game:
    def __init__(self, channel):
        self.channel = channel
        self.reset(keep_players=False)

    async def say(self, message):
        await self.channel.send(message)

    def get_player(self, client):
        try:
            player = next(p for p in self.players if p.client == client)
        except StopIteration:
            player = None
        return player

    def current_team(self):
        return Teams(self.current_step.value // 2)

    def current_role(self):
        return Roles(self.current_step.value % 2)

    def reset(self, keep_players=True):
        self.playing = False
        self.mode = None
        self.steps = None
        self.current_step = None
        if not keep_players:
            self.players = []
        self.words = []
        self.clue = None
        self.number = None
        self.turn = 0

class Player:
    def __init__(self, client, team, role):
        self.client = client
        self.team = team
        self.role = role

    @property
    def status(self):
        return Statuses((2 * self.team.value) + self.role.value)

class Word:
    def __init__(self, label, team):
        self.label = label
        self.team = team
        self.guessed = False

async def maybe_join(game, message, team):
    if game.playing:
        await game.say(f"{message.author.mention} Une partie est en cours, impossible de rejoindre une équipe.")
        return

    if len([p for p in game.players if p.team == team]) > 0:
        role = Roles.GUESSER
    else:
        role = Roles.CHOOSER

    player = game.get_player(message.author)
    if player:
        if player.team == team:
            await game.say(f"{message.author.mention} Tu fais déjà partie de cette équipe.")
            return
        else:
            player.team = team
            player.role = role
    else:
        player = Player(client=message.author, team=team, role=role)
        game.players.append(player)

    await game.say(f"{message.author.mention} Équipe {('rouge', 'bleue', 'neutre')[team.value]} rejointe, rôle : {('choisisseur', 'devineur')[role.value]}.")

async def maybe_change_role(game, message):
    wannabe = game.get_player(message.author)

    if not wannabe:
        await game.say(f"{message.author.mention} Tu n'es dans aucune équipe.")
        return

    if game.playing:
        await game.say(f"{message.author.mention} Une partie est en cours, impossible de changer de rôle.")
        return

    wannabe.role = Roles(int(not(wannabe.role.value)))

    await game.say(f"{message.author.mention} est désormais {('choisisseur', 'devineur')[wannabe.role.value]} de l'équipe {('rouge', 'bleue', 'neutre')[wannabe.team.value]}.")

async def print_teams(game):
    if not game.players:
        await game.say(f"Aucun joueur inscrit.")
        return

    output = ""

    for team in (Teams.RED, Teams.BLUE, Teams.NEUTRAL):
        output += f"{(REDDOT, BLUEDOT, WHITEDOT)[team.value]} Équipe {('rouge', 'bleue', 'neutre')[team.value]} :\n"
        for player in [p for p in game.players if p.team == team]:
            output += f"--- {(SPEAKING, GLASS)[player.role.value]} {player.client.name} ({('choisisseur', 'devineur')[player.role.value]})\n"

    await game.say(output)

async def print_configurations(game, with_error=False):

    output = ""

    if with_error:
        output += "La configuration actuelle des joueurs ne correspond à aucune configuration de jeu possible.\n\n"

    output += "__Configurations possibles__\n\n"

    possible_nb_of_players = sorted(set(sum(c.values()) for c in CONFIGURATIONS))

    for nb_players in possible_nb_of_players:
        output += f"**{nb_players} joueur{'s' if nb_players > 1 else ''}**\n"
        configurations = [c for c in CONFIGURATIONS if sum(c.values()) == nb_players]
        for configuration in configurations:
            statuses = list(configuration.elements())
            competition = any(e in [0, 1, 2, 3] for e in statuses)
            output += " + ".join([SYMBOLS[status] for status in statuses])
            if competition:
                output += f" (compétition {SWORDS})"
            else:
                output += f" (coopération {HANDSHAKE})"
            output += "\n"
        output += "\n"

    await game.say(output)

async def print_grid(game, revealed=False, to=Recipients.EVERYONE):
    output = ""

    if to == Recipients.CHOOSERS:
        output += "---------- Grille actuelle : ----------\n"

    widths = []
    for column in range(5):
        words_in_column = [word for (idx, word) in enumerate(game.words) if idx % 5 == column]
        widths.append(max(len(w.label) for w in words_in_column))

    for y in range(5):
        for x in range(5):
            word = game.words[y*5 + x]
            label = word.label + (" " * (widths[x] - len(word.label) + 5))
            label = f"`{label}`"
            if revealed and word.guessed:
                label = f"~~{label}~~"
            output += f"{(REDDOT, BLUEDOT, WHITEDOT, SKULL)[word.team.value] if (revealed or word.guessed) else QUESTION}{label}"
        output += "\n"

    if to == Recipients.EVERYONE:
        await game.say(output)
    elif to == Recipients.CHOOSERS:
        choosers = [p for p in game.players if p.role == Roles.CHOOSER]
        for chooser in choosers:
            await chooser.client.send(output)

async def maybe_leave(game, message):
    player = game.get_player(message.author)

    if not player:
        await game.say(f"{message.author.mention} Tu n'es dans aucune équipe.")
        return

    if game.playing:
        await game.say(f"{message.author.mention} Une partie est en cours, impossible quitter l'équipe.")
        return

    team = player.team
    game.players.remove(player)
    await game.say(f"{message.author.mention} est parti de l'équipe {('rouge', 'bleue', 'neutre')[team.value]}.")

async def maybe_start(game):
    if not game.players:
        await game.say(f"Aucun joueur inscrit.")
        return

    configuration = Counter([p.status for p in game.players])

    if not configuration in CONFIGURATIONS:
        await print_configurations(game, with_error=True)
        return

    game.playing = True
    if any(p.team in (Teams.RED, Teams.BLUE) for p in game.players):
        game.mode = Modes.COMPETITION
    else:
        game.mode = Modes.COOPERATION
    game.steps = CYCLES[game.mode]
    with open(CODENAMES_WORDS, "r") as f:
        lexicon = f.read().splitlines()
    game.words = [Word(label=word, team=Teams.NEUTRAL) for word in random.sample(lexicon, 25)]
    if game.mode == Modes.COMPETITION:
        for idx in range(0, 9):
            game.words[idx].team = Teams.RED
        for idx in range(9, 17):
            game.words[idx].team = Teams.BLUE
        game.words[17].team = Teams.BOMB
    elif game.mode == Modes.COOPERATION:
        for idx in range(0, 12):
            game.words[idx].team = Teams.BOMB
    random.shuffle(game.words)

    await proceed(game)

async def proceed(game):

    if game.current_step:

        scores = [len([w for w in game.words if w.guessed and w.team == team]) for team in (Teams.RED, Teams.BLUE, Teams.NEUTRAL)]
        if any(w for w in game.words if w.guessed and w.team == Teams.BOMB):
            if game.mode == Modes.COOPERATION:
                await game.say(f"{SAD} La bombe a gagné. Score final des neutres : **{scores[2]}/12** en {game.turn} tours.")
            elif game.mode == Modes.COMPETITION:
                winners = int(not(game.current_team()))
                await game.say(f"{PARTY} L'équipe {('rouge', 'bleue')[winners]} a gagné pour cause d'explosion de l'équipe adverse !")
            game.reset()
            return

        for team in (Teams.RED, Teams.BLUE, Teams.NEUTRAL):
            if [w for w in game.words if w.team == team] and not any(w for w in game.words if w.guessed == False and w.team == team):
                await game.say(f"{PARTY} L'équipe {('rouge', 'bleue', 'neutre')[team.value]} a gagné ! Elle a trouvé tous ses mots.")
                game.reset()
                return

    game.current_step = next(game.steps)
    current_players = [p.client.mention for p in game.players if p.status == game.current_step]

    if game.current_role() == Roles.CHOOSER:
        game.turn += 1
        if game.turn == 1:
            await print_grid(game, revealed=False, to=Recipients.EVERYONE)
        await print_grid(game, revealed=True, to=Recipients.CHOOSERS)
        await game.say(f"{SYMBOLS[game.current_step]}"
                                   f" C'est au choisisseur de l'équipe"
                                   f" {('rouge', 'bleue', 'neutre')[game.current_team().value]}"
                                   f" ({', '.join(current_players)}) de m'indiquer"
                                   f" **en privé** un indice et un nombre de mots souhaité.")
        return

    if game.current_role() == Roles.GUESSER:
        neutral_guessers = [p.client.mention for p in game.players if p.status == Statuses.NEUTRAL_GUESSER]
        current_players += neutral_guessers
        current_players = set(current_players)
        plural = len(current_players) > 1
        await game.say(f"{SYMBOLS[game.current_step]}"
                                   f" C'est au{('','x')[plural]} devineur{('','s')[plural]} de l'équipe"
                                   f" {('rouge', 'bleue', 'neutre')[game.current_team().value]}"
                                   f" ({', '.join(current_players)}) de retrouver la sélection"
                                   f" effectuée par le choisisseur. L'indice est **{game.clue}**."
                                   f" Nombre de mots à trouver : **{game.number}**")

async def process_whisper(game, message):
    player = game.get_player(message.author)

    if game.current_step != player.status:
        await message.author.send("Ce n'est pas à toi de me parler pour l'instant.")
        return

    content = message.content.strip()

    if game.current_role() == Roles.CHOOSER:
        if regex := re.search(r"^([^ ]+) (\d+)$", content, re.I):
            maybe_number = int(regex.group(2))
            number_max = len([w for w in game.words if w.guessed == False and w.team == game.current_team()])
            if not (1 <= maybe_number <= number_max):
                await message.author.send(f"Nombre invalide (doit être entre 1 et {number_max}).")
                return
            game.number = maybe_number
            
            maybe_clue = regex.group(1)
            if any(w for w in game.words if serialize(w.label) == serialize(maybe_clue)):
                await message.author.send(f"L'indice ne peut pas être un des mots de la grille !")
                return
            game.clue = maybe_clue

            await message.author.send(f"OK, ça continue sur {game.channel.mention} !")
            await proceed(game)
            return
        else:
            await message.author.send("Choisis secrètement un ou plusieurs mots, puis envoie (ici)"
                                      " `<indice> <nombre>`, par exemple `caisson 3`."
                                      " L'indice doit être un seul mot, et il ne doit pas être de"
                                      " la même famille qu'un mot de la grille !")
            return

    if game.current_role() == Roles.GUESSER:
        await message.author.send(f"Tu dois deviner le mot, ça se passe en public sur {game.channel.mention}.")

async def maybe_guess(game, message, content):

    if not game.playing:
        await game.say("Aucune partie en cours.")
        return

    player = game.get_player(message.author)
    if not player:
        await game.say(f"{message.author.mention} Tu n'es dans aucune équipe.")
        return

    if player.team != game.current_team() and player.team != Teams.NEUTRAL:
        await game.say(f"{message.author.mention} Ce n'est pas à ton équipe de jouer.")
        return

    if player.role == Roles.CHOOSER:
        await game.say(f"{message.author.mention} Tu es choisisseur, pas devineur.")
        return        

    if game.current_role() == Roles.CHOOSER:
        await game.say(f"{message.author.mention} Le choisisseur n'a pas encore donné son indice.")
        return        

    try:
        word = next(w for w in game.words if serialize(w.label) == serialize(content))
    except StopIteration:
        await game.say(f"{message.author.mention} Je ne reconnais pas ce mot dans la grille.")
        return
    if word.guessed:
        await game.say(f"{message.author.mention} Ce mot a déjà été deviné et révélé.")
        return

    word.guessed = True
    await print_grid(game, revealed=False, to=Recipients.EVERYONE)
    if word.team == game.current_team():
        await game.say(f"{SMILE} Bien ouej, c'est un mot de ton équipe !")
        game.number -= 1
        if game.number > 0:
            await game.say(f"Nombre de mots à trouver encore : {game.number}")
        else:
            await game.say(f"Le nombre de mots indiqué par le choisisseur a été atteint, bravo ! Fin du tour.")
            await proceed(game)
    else:
        game.number = 0
        if word.team == Teams.NEUTRAL:
            await game.say(f"{MEH} Oups, c'est un mot neutre... Fin du tour.")
        elif word.team == Teams.BOMB:
            await game.say(f"{BLOWN} **BOUM !** C'est {('une','la')[game.mode.value]} bombe ! Fin du jeu.")
        else:
            await game.say(f"{SAD} Mince... c'est un mot de l'équipe adverse... Fin du tour.")

        await proceed(game)
