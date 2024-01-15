
from enum import Enum
from typing import Optional, TypeAlias

class Format(Enum):
    BOLD = 1
    FAINT = 2
    ITALIC = 3
    UNDERLINE = 4
    BLINK = 5
    FAST_BLINK = 6
    REVERSE = 7
    CONCEAL = 8
    STRIKE = 9

class Color(Enum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    BRIGHT_BLACK = 90
    BRIGHT_RED = 91
    BRIGHT_GREEN = 92
    BRIGHT_YELLOW = 93
    BRIGHT_BLUE = 94
    BRIGHT_MAGENTA = 95
    BRIGHT_CYAN = 96
    BRIGHT_WHITE = 97
    BG_BLACK = 40
    BG_RED = 41
    BG_GREEN = 42
    BG_YELLOW = 43
    BG_BLUE = 44
    BG_MAGENTA = 45
    BG_CYAN = 46
    BG_WHITE = 47
    BG_BRIGHT_BLACK = 100
    BG_BRIGHT_RED = 101
    BG_BRIGHT_GREEN = 102
    BG_BRIGHT_YELLOW = 103
    BG_BRIGHT_BLUE = 104
    BG_BRIGHT_MAGENTA = 105
    BG_BRIGHT_CYAN = 106
    BG_BRIGHT_WHITE = 107

class Color256:
    __n: int
    is_bg: bool

    def __init__(self, n: int, is_bg: bool = False) -> None:
        if not (0 <= n <= 255):
            raise Exception(f"Invalid 256bit color number: {n}")
        self.__n = n
        self.is_bg = is_bg

    def __str__(self) -> str:
        tag: str = "48" if self.is_bg else "38"
        return f"{tag};5;{self.__n}"

class ColorRGB:
    _r: int
    _g: int
    _b: int
    is_bg: bool

    def __init__(self, r: int, g: int, b: int, is_bg: bool = False) -> None:
        for k, n in {"R": r, "G": g, "B": b}.items():
            if not (0 <= n <= 255):
                raise Exception(f"Invalid 256bit color number: {k}:{n}")
        self._r = r
        self._g = g
        self._b = b
        self.is_bg = is_bg

    def __str__(self) -> str:
        tag: str = "48" if self.is_bg else "38"
        return f"{tag};2;{self._r};{self._g};{self._b}"

StyleElement: TypeAlias = Color | Color256 | ColorRGB | Format | int

Style = list[StyleElement] | StyleElement

def styled(text: str, style: Style = []) -> str:
    if isinstance(style, list):
        for s in style:
            text = __styled(text, s)
        return text
    else:
        return __styled(text, style)

def __styled(text: str, style: StyleElement) -> str:
    if isinstance(style, (Color, Format)):
        value = style.value
    else:
        value = style
    return f"\033[{value}m{text}\033[m"