import re

a = open("output.bin", "wb")

def remove_escape_sequences(line: str) -> str:
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    line = ansi_escape.sub('', line)
    line = line.replace('\r', '')

    a.write(line.encode("utf-8") + b"\n")

    return line
