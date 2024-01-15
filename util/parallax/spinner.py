from typing import Collection

# for more spinner strings see https://raw.githubusercontent.com/sindresorhus/cli-spinners/main/spinners.json

class Spinner:
    _spinner: list[str]
    _index: int
    
    @staticmethod
    def dots(offset: int = 0) -> "Spinner":
        return Spinner(spinner="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", offset=offset)
    
    @staticmethod
    def line(offset: int = 0) -> "Spinner":
        return Spinner(spinner=["-", "\\", "|", "/"], offset=offset)
    
    @staticmethod
    def ellipsis(offset: int = 0) -> "Spinner":
        return Spinner(spinner=["   ", ".  ", ".. ", "...", ".. ", ".  ", "   "], offset=offset, factor=2)
    
    @staticmethod
    def scrolling(offset: int = 0) -> "Spinner":
        return Spinner(spinner=[".  ", ".. ", "...", " ..", "  .", "   "], offset=offset)
    
    @staticmethod
    def soccer(offset: int = 0) -> "Spinner":
        return Spinner(spinner=[
            "=🧑⚽️       🧑 ",
            "🧑  ⚽️      🧑 ",
            "🧑   ⚽️     🧑 ",
            "🧑    ⚽️    🧑 ",
            "🧑     ⚽️   🧑 ",
            "🧑      ⚽️  🧑 ",
            "🧑       ⚽️🧑= ",
            "🧑      ⚽️  🧑 ",
            "🧑     ⚽️   🧑 ",
            "🧑    ⚽️    🧑 ",
            "🧑   ⚽️     🧑 ",
            "🧑  ⚽️      🧑 "
        ], offset=offset)
        
    @staticmethod
    def pong(offset: int = 0) -> "Spinner":
        return Spinner(spinner= [
            "▐⠂       ▌",
            "▐⠈       ▌",
            "▐ ⠂      ▌",
            "▐ ⠠      ▌",
            "▐  ⡀     ▌",
            "▐  ⠠     ▌",
            "▐   ⠂    ▌",
            "▐   ⠈    ▌",
            "▐    ⠂   ▌",
            "▐    ⠠   ▌",
            "▐     ⡀  ▌",
            "▐     ⠠  ▌",
            "▐      ⠂ ▌",
            "▐      ⠈ ▌",
            "▐       ⠂▌",
            "▐       ⠠▌",
            "▐       ⡀▌",
            "▐      ⠠ ▌",
            "▐      ⠂ ▌",
            "▐     ⠈  ▌",
            "▐     ⠂  ▌",
            "▐    ⠠   ▌",
            "▐    ⡀   ▌",
            "▐   ⠠    ▌",
            "▐   ⠂    ▌",
            "▐  ⠈     ▌",
            "▐  ⠂     ▌",
            "▐ ⠠      ▌",
            "▐ ⡀      ▌",
            "▐⠠       ▌"
        ], offset=offset)
        

    def __init__(self, spinner: list[str] | str, offset: int = 0, factor: int = 1) -> None:
        spinner_list: list[str] = []

        for element in spinner:
            for _ in range(factor):
                spinner_list.append(element)

        self._spinner = spinner_list
        self._index = offset
        
    def next(self) -> str:
        self._index = (self._index + 1) % len(self._spinner)
        return self._spinner[self._index]