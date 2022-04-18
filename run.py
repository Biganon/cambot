import sys
import discord
import hashlib
import re
import asyncio
import random
from datetime import datetime
import cambot.codenames as codenames
import cambot.wordle as wordle
import cambot.ephemeris as ephemeris
from cambot.emojis import *
from cambot.settings import *

bot = discord.Client()
codenames_games = {}
wordle_games = {}

# Startup
@bot.event
async def on_ready():
    print(f"Connecté, nom {bot.user.name}, id {bot.user.id}")
    for channel_id in CODENAMES_CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        codenames_game = codenames.Game(channel)
        codenames_games[channel_id] = codenames_game
        print(f"Écoute pour Codenames sur {channel.guild} > {channel.name}")
    for channel_id in WORDLE_CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        wordle_game = wordle.Game(channel)
        wordle_games[channel_id] = wordle_game
        print(f"Écoute pour Wordle sur {channel.guild} > {channel.name}")

    current_date = None
    while True:
        await asyncio.sleep(HEARTBEAT)
        now = datetime.now()
        if now.date() != current_date: # the bot was just started, OR it's a new day
            events_done = [event[1] < now.time() for event in EVENTS] # mark events in the past as done
            current_date = now.date()
        for idx, event in enumerate(EVENTS):
            if event[1] <= now.time() and not events_done[idx]:
                events_done[idx] = True
                if event[0] == EPHEMERIS:
                    embed = ephemeris.digest()
                    for channel_id in EPHEMERIS_CHANNEL_IDS:
                        await bot.get_channel(channel_id).send(embed=embed)
                elif event[0] == WORDLE:
                    for wordle_game in wordle_games.values():
                        await wordle_game.reset()

# Receiving a message
@bot.event
async def on_message(message):

    # Ignore own messages
    if message.author == bot.user:
        return

    content = message.content.strip()
    content_lowercase = content.lower()

    # Private messages
    if isinstance(message.channel, discord.channel.DMChannel):
        games_entered = [codenames_game for codenames_game in codenames_games.values() if codenames_game.get_player(message.author)]

        # Admin commands
        if message.author.name == "Biganon" and message.author.discriminator == "0001":
            if regex := re.search(r"^[sS]ay ([0-9]+) (.*)$", content):
                channel_id = int(regex.group(1))
                to_say = regex.group(2)
                await bot.get_channel(channel_id).send(to_say)

            if regex := re.search(r"^wordle targets?$", content_lowercase):
                output = ""
                for wordle_game in wordle_games.values():
                    output += f"{wordle_game.channel.guild} > {wordle_game.channel.name} : {wordle_game.target}\n"
                await message.author.send(output)

            if regex := re.search(r"^wordle reset ([0-9]+)$", content_lowercase):
                channel_id = int(regex.group(1))
                await wordle_games[channel_id].reset()

        # Codenames whispers
        if len(games_entered) == 1:
            await codenames.process_whisper(games_entered[0], message)
        elif len(games_entered) > 1:
            await message.author.send(f"Tu es inscrit dans plusieurs parties en même temps, je ne peux pas travailler dans ces conditions.")
        else:
            pass

        return

    # Help
    if re.search(r"^!(aide|help|commandes)$", content_lowercase):
        await print_help(message.channel)

    # Judge something
    if regex := re.search(r"^!juger (.+)$", content_lowercase):
        subject = regex.group(1).strip()
        score = int(hashlib.md5(bytes(subject.lower(), "utf-8")).hexdigest(), 16) % 2
        opinion = ("c'est hyper bien", "c'est tellement pas OK")[score]
        output = '{}, {}'.format(subject, opinion)
        await message.channel.send(output)

    # Dice
    if regex := re.search(r"^!(?P<number>\d+)?d[eé]s?(?P<maximum>\d+)?$", content_lowercase):
        thrower = message.author.display_name
        maximum = 6
        try:
            maximum = int(regex.group("maximum"))
        except (TypeError, ValueError):
            pass

        number = 1
        try:
            number = int(regex.group("number"))
        except (TypeError, ValueError):
            pass

        results = []
        for n in range(number):
            result = random.randint(1, maximum)
            results.append(result)

        output = f"Résultat du lancer de {thrower} : **{sum(results)}**"
        if len(results) > 1:
            output += f" ({', '.join(map(str, results))})"

        await message.channel.send(output)

    # Codenames commands
    if message.channel.id in codenames_games.keys():

        game = codenames_games[message.channel.id]

        if re.search(r"^!rouges?$", content_lowercase):
            await codenames.maybe_join(game, message, codenames.Teams.RED)

        elif re.search(r"^!bleus?$", content_lowercase):
            await codenames.maybe_join(game, message, codenames.Teams.BLUE)

        elif re.search(r"^!neutres?$", content_lowercase):
            await codenames.maybe_join(game, message, codenames.Teams.NEUTRAL)

        elif re.search(r"^!r[oô]les?$", content_lowercase):
            await codenames.maybe_change_role(game, message)

        elif re.search(r"^![eé]quipes?$", content_lowercase):
            await codenames.print_teams(game)

        elif re.search(r"^!config(uration)?s?$", content_lowercase):
            await codenames.print_configurations(game)

        elif re.search(r"^!(partir|quitter)$", content_lowercase):
            await codenames.maybe_leave(game, message)

        elif re.search(r"^!(jouer|play|start)$", content_lowercase):
            await codenames.maybe_start(game)

        elif regex := re.search(r"^!deviner (.+)$", content_lowercase):
            await codenames.maybe_guess(game, message, regex.group(1))

    # Wordle
    if message.channel.id in wordle_games.keys():
        await wordle_games[message.channel.id].parse(message)

# Help
async def print_help(channel):
    output = """__Commandes de CamBot__

    **Divers**
    !juger `truc` : demander à Camille/CamBot de juger `truc`
    !XdésY : lancer X dé(s) à Y faces. Le "s" de "dés" est optionnel. Si omis, X vaut 1 et Y vaut 6

    **Codenames**
    !rouge : rejoindre l'équipe rouge
    !bleu : rejoindre l'équipe bleue
    !neutre : rejoindre l'équipe neutre
    !role : changer de rôle dans son équipe
    !equipes : afficher la composition des équipes
    !configurations : afficher les configurations de jeu possibles
    !partir : quitter une équipe
    !jouer : lancer la partie
    !deviner `mot` : deviner le mot `mot`

    **Divers**
    !aide : afficher ce message
    """
    await channel.send(output)

# Let unprivileged users pin messages
async def reaction_changed(payload):
    emoji = payload.emoji
    if not emoji.is_unicode_emoji():
        return
    if(len(emoji.name) != 1): # flags, Fitzpatrick skin tone, variation selectors...
        return
    if emoji.name != PUSHPIN:
        return
    event_type = payload.event_type
    message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
    if event_type == "REACTION_ADD":
        await message.pin()
    elif event_type == "REACTION_REMOVE":
        await message.unpin()

@bot.event
async def on_raw_reaction_add(payload):
    await reaction_changed(payload)

@bot.event
async def on_raw_reaction_remove(payload):
    await reaction_changed(payload)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
