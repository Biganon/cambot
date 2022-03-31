import sys
import re
from unidecode import unidecode

file = sys.argv[1]

if file == "-":
    lines = sys.stdin
else:
    with open(file, "r") as f:
        lines = f.read().splitlines()

output = set()
for line in lines:
    wordlized = unidecode(line).strip().upper()
    if not re.match(r"^[A-Z]*$", wordlized): # ignore words with dashes, apostrophes...
        continue
    output.add(wordlized)

output = sorted(list(output))

for line in output:
    print(line)