import tty
from typing import IO
import sys
import shutil
import threading
import queue

import util

class SingleLinePrinter:
    _index: int | None # none if not root
    _message: str = ''
    _subprinters: list["SingleLinePrinter"] 
    _indent_str: str = ""
    _base_printer: "MultilinePrinter | None"
    _parent: "SingleLinePrinter | None"

    @staticmethod
    def make_root(index: int | None, multiline_printer: "MultilinePrinter") -> "SingleLinePrinter":
        return SingleLinePrinter(index=index, parent=None, base_printer=multiline_printer)

    def __init__(self, index: int | None, parent: "SingleLinePrinter | None" = None, base_printer: "MultilinePrinter | None" = None) -> None:
        self._parent = parent
        self._subprinters = []
        self._base_printer = base_printer
        self._index = index
        self._parent = parent

    def print(self, message: str):
        self._message = message
        root = self._get_root()
        if root._base_printer is not None:
            root._base_printer._add_print_request(root)
        else:
            raise Exception("MultilinePrinter is not initialized")

    def subprinter(self) -> "SingleLinePrinter":
        printer = SingleLinePrinter(index=None, parent=self)
        self._subprinters.append(printer)
        return printer
    
    def _get_root(self) -> "SingleLinePrinter":
        if self._parent is None:
            return self
        return self._parent._get_root()

    def _format(self) -> str:
        if len(self._subprinters) == 0:
            return self._message

        result = self._message
        for subprinter in self._subprinters:
            result += '\n' + subprinter._format()

        return result

class MultilinePrinter:        

    nlines: int
    
    out: IO[str]
    
    terminal_width: int

    command_name: str | None = None

    enabled = True
    
    _all_messages: list[str]
    
    _already_printed: bool = False

    _print_thread: threading.Thread

    _print_queue: queue.Queue[tuple[str, int]]

    _finished: bool = False

    _line_flashed = 0

    _printers: list[SingleLinePrinter] 

    def __init__(self, nlines: int, out: IO[str] = sys.stdout, disable_input: bool = True, command_name: str | None = None) -> None:
        self.nlines = nlines
        self.command_name = command_name
        self._print_queue = queue.Queue()
        self.out = out
        self.terminal_width = self._get_width()
        self._all_messages = [''] * nlines
        self._printers = [SingleLinePrinter.make_root(i, self) for i in range(nlines)]
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
                message, line = self._print_queue.get(block=True, timeout=0.1)
                message = self._with_command_name(message)
                self._all_messages[line] = message
                self._update()
            except queue.Empty:
                pass

    def _with_command_name(self, message: str) -> str:
        if self.command_name is None:
            return message
        return f"\033[0;34m[{self.command_name}]\033[0m {message}"

    def _get_width(self):
        try:
            columns = shutil.get_terminal_size().columns
            return columns
        except AttributeError:
            return 0
        
    def _update(self):
        if self._already_printed:
            self._erase_print_area()
        self._update_messages()
        self._already_printed = True

    def _calc_lines(self, line: str) -> int:
        def calc_line(line: str) -> int:
            nlines = 0
            while True:
                if len(line) <= self.terminal_width:
                    nlines += 1
                    break
                else:
                    nlines += 1
                    line = line[self.terminal_width:]

            return nlines
            
        line = util.remove_escape_sequences(line)

        lines = line.split('\n')

        nlines = 0
        for line in lines:
            nlines += calc_line(line)

        return nlines
    
    def _update_messages(self):
        if not self.enabled:
            return
        self._line_flashed = 0
        for i in range(self.nlines):
            self._line_flashed += self._calc_lines(self._all_messages[i])
            self.out.write(self._all_messages[i])
            self.out.write('\n')

    def _erase_print_area(self):
        if not self.enabled:
            return
        if self._line_flashed == 0:
            return

        code = '\033[1G' + '\033[A'*(self._line_flashed) + '\033[0J'
        # '\033[1G' move the cursor to the beginning of the line
        # '\033[A' move the cursor up
        # '\033[0J' clear from cursor to end of screen

        self.out.write(code)
        self.out.flush()
