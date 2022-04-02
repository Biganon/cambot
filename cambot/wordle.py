import random
import re
from unidecode import unidecode
from collections import defaultdict
from .settings import *

with open(WORDLE_VALID_WORDS, "r") as f:
    valid_words = set(f.read().splitlines())

with open(WORDLE_TARGET_WORDS, "r") as f:
    target_words = set(f.read().splitlines())

valid_words = valid_words.union(target_words)

def validate(target, guess):
    assert len(target) == len(guess)

    copy = list(target)
    output = [0] * len(target)

    # Look for the green squares :

    for idx in range(len(target)):
        if target[idx] == guess[idx]:
            output[idx] = 2
            copy[idx] = None

    # Look for the yellow squares :

    for idx in range(len(target)):
        if target[idx] == guess[idx]:
            continue # ignore the letters that are green
        if guess[idx] in copy:
            left_most_yellow_idx = copy.index(guess[idx])
            output[idx] = 1
            copy[left_most_yellow_idx] = None # mark ONE of the corresponding letters as done

    return output

class Game:
    def __init__(self, channel):
        self.channel = channel
        self.target = None
        self.winner = None
        self.tries = 0
        self.last_player = None
        self.scores = None
        self.tried = None 

    async def reset(self):
        self.target = random.choice(tuple(x for x in target_words if len(x) >= WORDLE_MINLENGTH))
        self.winner = None
        self.tries = 0
        self.last_player = None
        self.scores = defaultdict(int)
        self.tried = set()
        await self.channel.edit(slowmode_delay=WORDLE_SLOWMODE)
        await self.channel.send(f"Il y a un nouveau mot à deviner ! Il fait {len(self.target)} lettres.")

    async def parse(self, message):
        guess = unidecode(message.content.strip()).upper()

        # if somebody won
        if self.winner:
            return

        # if the game was never initialized
        if not self.target:
            return

        # if the message is not comprised of letters (with or without accents) only
        if not re.match(r"^[A-Z]*$", guess):
            return

        # if the guess is obviously not the same length
        ratio = 2/3
        if len(guess) <= len(self.target) * ratio or len(self.target) <= len(guess) * ratio:
            return

        if WORDLE_FORCE_ALTERNATION and message.author == self.last_player:
            await self.channel.send(f"{message.author.mention} Laisse un peu jouer les autres !")
            return            
        if len(guess) != len(self.target):
            await self.channel.send(f"{message.author.mention} Le mot à deviner fait {len(self.target)} lettres (ça ne compte pas comme un tour).")
            return
        if guess not in valid_words:
            await self.channel.send(f"{message.author.mention} `{guess}` n'est pas dans mon dictionnaire (ça ne compte pas comme un tour).")
            return

        self.tries += 1
        self.last_player = message.author
        result = validate(self.target, guess)
        points = 0
        for idx, letter in enumerate(guess):
            if (idx, letter) in self.tried:
                continue
            points += WORDLE_POINTS[result[idx]]
            self.tried.add((idx, letter))

        output_word = " ".join(f":regional_indicator_{x.lower()}:" for x in guess)
        output_squares = " ".join((":white_large_square:", ":yellow_square:", ":green_square:")[x] for x in result)

        output = f"{message.author.mention} (essai {self.tries}, {points} point{'s' if points > 1 else ''})\n{output_word}\n{output_squares}"
        self.scores[message.author] += points

        if guess == self.target:
            self.winner = message.author
            await self.channel.edit(slowmode_delay=0)
            output += "\n\n:trophy: YOUPI :trophy:\n\nScores :\n\n"
            for idx, score in enumerate(sorted(self.scores.items(), key=lambda x:x[1], reverse=True)):
                player, points = score
                output += f"{idx+1}) {player.display_name} ({points} point{'s' if points > 1 else ''})\n"

        await self.channel.send(output)
