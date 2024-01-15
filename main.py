import shutil
import unicodedata

import util
import util.parallax as parallax
import util.style as style
import time

terminal_width = shutil.get_terminal_size().columns

def line_to_components(line: str) -> list[int]:
    components: list[int] = []
    for char in line:
        if unicodedata.east_asian_width(char) in 'FW':
            components.append(2)
        else:
            components.append(1)

    return components

def lines_in_terminal(text: str) -> int:
    text = util.remove_escape_sequences(text)
    lines = text.split('\n')

    number_of_lines = 0
    current_column = 0

    for line in lines:
        components = line_to_components(line)

        print(components, len(components), terminal_width)

        number_of_lines += 1

        for component in components:
            current_column += component
            if current_column > terminal_width:
                current_column = component
                number_of_lines += 1

    return number_of_lines


text = "a" * 100

lines = lines_in_terminal(text)
print(text)
print(lines)