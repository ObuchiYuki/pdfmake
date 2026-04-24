#
# regex_choice.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

import re


class RegexChoice:
    """argparse choices that accept regex patterns."""

    def __init__(self, pattern: str):
        self.pattern = pattern

    def __contains__(self, val: str) -> bool:
        return re.match(self.pattern, val) is not None

    def __iter__(self):
        return iter([self.pattern])
