import tty
from typing import IO
import sys
import shutil
import threading
import queue
import unicodedata

import util

"""
Use with tqdm:
    from tqdm import tqdm

    printer = MultilinePrinter(nlines=2)
    printer0 = printer.printer(0)
    printer1 = printer.printer(1)

    for i in tqdm(range(100), file=printer0, ncols=printer0.ncols):
        printer1.print(f"i: {i}")
"""

debug_file = open("debug.txt", "w")

class SingleLinePrinter:
    _index: int | None # none if not root
    _message: str = ""
    _prefix: str = ""
    _subprinters: list["SingleLinePrinter"] 
    _base_printer: "MultilinePrinter | None"
    _parent: "SingleLinePrinter | None"

    @property
    def prefix(self) -> str:
        return self._prefix
    
    @prefix.setter
    def prefix(self, value: str):
        self._prefix = value
        self.flush()

    @staticmethod
    def make_root(index: int | None, prefix: str, multiline_printer: "MultilinePrinter") -> "SingleLinePrinter":
        return SingleLinePrinter(index=index, parent=None, base_printer=multiline_printer, prefix=prefix)
    
    @property
    def ncols(self) -> int:
        root = self._get_root()
        if root._base_printer is None: return 0
        return root._base_printer.terminal_width - len(util.remove_escape_sequences(self._prefix))

    def __init__(self, index: int | None, prefix: str, parent: "SingleLinePrinter | None" = None, base_printer: "MultilinePrinter | None" = None) -> None:
        self._parent = parent
        self._prefix = prefix
        self._subprinters = []
        self._base_printer = base_printer
        self._index = index
        self._parent = parent

    def clear(self):
        self._message = ''

    def write(self, message: str): # for tqdm
        message = message.replace('\n', '').replace('\r', '')
        if len(message) == 0:
            return
        self.print(message)
        
    def flush(self):
        root = self._get_root()
        if root._base_printer is not None:
            root._base_printer._add_print_request(root)

    def print(self, message: str):
        self._message = message
        self.flush()

    def subprinter(self, prefix = "") -> "SingleLinePrinter":
        printer = SingleLinePrinter(index=None, parent=self, prefix=prefix)
        self._subprinters.append(printer)
        return printer
    
    def _get_root(self) -> "SingleLinePrinter":
        if self._parent is None:
            return self
        return self._parent._get_root()

    def _format(self) -> str:
        if len(self._subprinters) == 0:
            return self._prefix + self._message

        result = self._message
        for subprinter in self._subprinters:
            result += '\n' + subprinter._format()

        return self._prefix + result

class MultilinePrinter:        

    nlines: int
    
    out: IO[str]
    
    terminal_width: int

    enabled = True
    
    _all_messages: list[str]
    
    _already_printed: bool = False

    _print_thread: threading.Thread

    _print_queue: queue.Queue[tuple[str, int]]

    _finished: bool = False

    _line_flashed = 0

    _printers: list[SingleLinePrinter] 

    def __init__(self, nlines: int, out: IO[str] = sys.stdout, disable_input: bool = True, root_prefix: str = "") -> None:
        self.nlines = nlines
        self._print_queue = queue.Queue()
        self.out = out
        self.terminal_width = self._get_width()
        self._all_messages = [''] * nlines
        self._printers = [SingleLinePrinter.make_root(i, root_prefix, self) for i in range(nlines)]
        if disable_input:
            try:
                tty.setcbreak(sys.stdin.fileno()) # 標準入力を無効化
            except:
                # 無効化できない場合は無視
                pass
        self._print_thread = threading.Thread(target=self._loop_over_queue)
        self._print_thread.start()

    def printer(self, line: int) -> "SingleLinePrinter":
        assert line < self.nlines, "line is out of range"
        return self._printers[line]
        
    def _add_print_request(self, printer: SingleLinePrinter):
        if not self.enabled:
            return
        if printer._index is None:
            return
        message = printer._format()
        self._print_queue.put((message, printer._index))

    def terminate(self):
        self._finished = True

    def _loop_over_queue(self):
        while not self._finished or not self._print_queue.empty():
            try:
                message, line = self._print_queue.get(block=True, timeout=0.05)
                self._all_messages[line] = message
                self._update()
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break

    def _get_width(self):
        try:
            columns = shutil.get_terminal_size().columns
            return columns
        except AttributeError:
            return 0
        
    def _update(self):
        head = ""
        if self._already_printed:
            head = self._erase_print_area()
        body = self._update_messages()
        self.out.write(head + body)
        self.out.flush()
        self._already_printed = True


    def _line_to_components(self, line: str) -> list[int]:
        components: list[int] = []
        for char in line:
            if unicodedata.east_asian_width(char) in 'FW':
                components.append(2)
            else:
                components.append(1)

        return components

    def _lines_in_terminal(self, text: str) -> int:
        text = util.remove_escape_sequences(text)
        lines = text.split('\n')

        number_of_lines = 0
        current_column = 0

        for line in lines:
            components = self._line_to_components(line)

            factor = 1
            current_column = 0

            for component in components:
                current_column += component
                if current_column > self.terminal_width:
                    current_column = component
                    factor += 1
            
            number_of_lines += factor
    
        return number_of_lines
    
    def _update_messages(self) -> str:
        self._line_flashed = 0
        
        res = ""
        for i in range(self.nlines):
            self._line_flashed += self._lines_in_terminal(self._all_messages[i])
            res += self._all_messages[i] + '\n'
            
        return res

    def _erase_print_area(self) -> str:
        if self._line_flashed == 0:
            return ""

        code = '\033[1G' + '\033[A'*(self._line_flashed) + '\033[0J'
        # '\033[1G' move the cursor to the beginning of the line
        # '\033[A' move the cursor up
        # '\033[0J' clear from cursor to end of screen

        return code
