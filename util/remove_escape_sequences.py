import re

def remove_escape_sequences(line: str) -> str:
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    line = ansi_escape.sub('', line)

    return line
