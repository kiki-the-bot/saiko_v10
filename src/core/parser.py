import re
from typing import Tuple, Optional

class ChaosParser:

    def __init__(self):
        self.word_map = {
               'ZERO': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4',
               'FIVE': '5', 'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9',
               'NANCY': '9', 'OH': '0',
               'WHISKEY': 'W', 'WILLIAM': 'W', 'HOTEL': 'H', 'HENRY': 'H',
               'NOVEMBER': 'N', 'CHARLIE': 'C', 'GOLF': 'G', 'WATER': 'W',
               'JULIET': 'J', 'KILO': 'K'
               }

        self.direct_pattern = re.compile(r'([A-Z]{2}[ -]?\d{8,10})\b')
        self.cleanup_pattern = re.compile(r'\b([A-Z])\s+AS\s+IN\s+\w+')
        self.split_pattern = re.compile(r'[^A-Z0-9]+')

    def parse(self, text: str, current_buffer: str) -> Tuple[str, str, Optional[str]]:

          clean_text = text.upper()
          direct_match = self.direct_pattern.search(clean_text)

          if direct_match:
               clean_id = direct_match.group(1).replace(" ", "").upper()
               return "LOCKED", "", clean_id

          clean_text = self.cleanup_pattern.sub(r'\1', clean_text)
          tokens = []
          for t in self.split_pattern.split(clean_text):
                    if t in self.word_map: tokens.append(self.word_map[t])
                    elif t.isalnum() and len(t) == 1: tokens.append(t)
                    elif t.isdigit(): tokens.append(t)

          new_buffer = current_buffer + "".join(tokens)
          match = self.direct_pattern.search(new_buffer)
          if match:
               return "LOCKED", "", match.group(1)

          if len(new_buffer) > 0:
               return "HUNTING", new_buffer, None
          return "EMPTY", "", None