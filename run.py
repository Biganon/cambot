import nextcord
import hashlib
import re
import asyncio
import random
import base64
import emoji
from datetime import datetime
import cambot.codenames as codenames
import cambot.wordle as wordle
import cambot.ephemeris as ephemeris
import cambot.polls as polls
from cambot.emojis import *
from cambot.settings import *

intents = nextcord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = nextcord.Client(intents=intents)
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
    if isinstance(message.channel, nextcord.channel.DMChannel):
        games_entered = [codenames_game for codenames_game in codenames_games.values() if codenames_game.get_player(message.author)]

        # Admin commands
        if message.author.name == "biganon":
            if regex := re.search(r"^[sS]ay ([0-9]+) (.*)$", content):
                channel_id = int(regex.group(1))
                to_say = regex.group(2)
                await bot.get_channel(channel_id).send(to_say)

            if regex := re.search(r"^[wW]ordle targets?$", content_lowercase):
                output = ""
                for wordle_game in wordle_games.values():
                    output += f"{wordle_game.channel.guild} > {wordle_game.channel.name} : {wordle_game.target}\n"
                await message.author.send(output)

            if regex := re.search(r"^[wW]ordle reset ([0-9]+)$", content_lowercase):
                channel_id = int(regex.group(1))
                await wordle_games[channel_id].reset()

            if regex := re.search(r"^[eE]phemeris$", content_lowercase):
                embed = ephemeris.digest()
                for channel_id in EPHEMERIS_CHANNEL_IDS:
                    await bot.get_channel(channel_id).send(embed=embed)

            if regex := re.search(r"^[dD]ump ([0-9]+)$", content):
                guild_id = int(regex.group(1))
                guild = bot.get_guild(guild_id)
                string = ",".join(channel.name for channel in guild.text_channels)
                b64 = base64.b64encode(string.encode("utf-8")).decode()
                await message.author.send(string)
                await message.author.send(b64)

            if regex := re.search(r"[lL]oad ([0-9]+) (.*)$", content):
                guild_id = int(regex.group(1))
                guild = bot.get_guild(guild_id)
                b64 = regex.group(2)
                string = base64.b64decode(b64.encode("utf-8")).decode()
                names = string.split(",")
                if len(names) != len(guild.text_channels):
                    await message.author.send(f"Erreur : {len(names)} noms fournis, mais {len(guild.text_channels)} canaux trouvés")
                    return
                for idx, channel in enumerate(guild.text_channels):
                    await channel.edit(name=names[idx])

            if regex := re.search(r"[pP]refix ([0-9]+) (.*)$", content):
                guild_id = int(regex.group(1))
                guild = bot.get_guild(guild_id)
                prefix = regex.group(2)
                for channel in guild.text_channels:
                    if emoji.is_emoji(channel.name[0]):
                        unprefixed = channel.name[1:]
                    else:
                        unprefixed = channel.name
                    await channel.edit(name=prefix+unprefixed)

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

    # Polls
    bullet = r"(\b[a-zA-Z]\))"
    if re.search(bullet, content):
        parts = re.split(bullet, content) # split at x) bullets, and keep them (hence the capturing group)
        parts = [stripped for part in parts if (stripped := part.strip())] # keep only non-empty-when-stripped parts (and strip them)
        if re.fullmatch(bullet, parts[0]): # the first part is a bullet (i.e. no introductory text)
            intro = ""
        else:
            intro = parts.pop(0)
        poll = polls.Poll()
        poll.owner = message.author
        poll.intro = intro
        for part in parts:
            if re.fullmatch(bullet, part): # the part is a bullet
                letter = part[0].lower()
            else: # the part is an option
                poll.options[letter] = part
        if len(poll.options) < 2:
            pass
        elif len(poll.options) > 20:
            await message.channel.send("Erreur : 20 options maximum")
        else:
            output = f"{intro}\n\n"
            for pair in sorted(poll.options.items(), key=lambda x:x[0]):
                letter, option = pair
                output += f":regional_indicator_{letter}: {option}\n"
            poll.message = await message.channel.send(output, view=polls.ButtonView(owner=poll.owner))
            for letter in sorted(poll.options.keys()):
                await poll.message.add_reaction(LETTERS[letter])

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

    **Sondages**
    Question ? a) Option b) Autre option c) Etc.

    **Aide**
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
