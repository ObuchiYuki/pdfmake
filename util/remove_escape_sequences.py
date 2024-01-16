import re

ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
ansi_escape_without_style = re.compile(r'\x1B\[([0-?]*)([ -/]*)([@-LN-ln-~])')

def remove_escape_sequences(line: str) -> str:
    line = ansi_escape.sub('', line)
    line = line.replace('\r', '')
    return line

def remove_escape_sequences_except_styling(text):
    line = ansi_escape_without_style.sub(r'------ \1 \2 \3 ------', text)
    line = line.replace('\r', '')
    return line
