import unidecode
from enum import Enum

def serialize(string):
    return unidecode.unidecode(string.lower().strip().replace(" ", "").replace("-", "").replace("'", "").replace(".", ""))

class EnumZero(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count