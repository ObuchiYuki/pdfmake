#
# remove_escape_sequences.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

import re

_ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
_ansi_escape_without_style = re.compile(r'\x1B\[([0-?]*)([ -/]*)([@-LN-ln-~])')


def remove_escape_sequences(line: str) -> str:
    line = _ansi_escape.sub('', line)
    line = line.replace('\r', '')
    return line


def remove_escape_sequences_except_styling(text: str) -> str:
    line = _ansi_escape_without_style.sub(r'------ \1 \2 \3 ------', text)
    line = line.replace('\r', '')
    return line
