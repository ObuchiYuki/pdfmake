#
# parallax_printer.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

"""
Actor-based dynamic multi-line terminal printer.

Unlike MultilinePrinter (fixed line count), ParallaxPrinter supports
adding and removing lines at runtime.  All mutable state lives inside
the actor; Line handles communicate exclusively via messages.
"""

from typing import IO, Any
import sys
import shutil
import threading
import re
import unicodedata
import tty

from pdfmake.util.parallax.actor import Actor

_ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')


def _remove_escape_sequences(line: str) -> str:
    return _ansi_escape.sub('', line).replace('\r', '')


# ---------------------------------------------------------------------------
# Internal state (actor thread only)
# ---------------------------------------------------------------------------

class _LineState:
    __slots__ = ("prefix", "message", "parent_id", "children")

    def __init__(self, prefix: str, parent_id: int | None) -> None:
        self.prefix = prefix
        self.message = ""
        self.parent_id = parent_id
        self.children: list[int] = []


# ---------------------------------------------------------------------------
# Handle (thread-safe, sends messages only)
# ---------------------------------------------------------------------------

class Line:
    """Thread-safe handle to a line inside a ParallaxPrinter actor."""

    _actor: "ParallaxPrinter"
    _id: int
    _ncols: int
    _prefix: str
    _cached_message: str

    def __init__(self, actor: "ParallaxPrinter", line_id: int, prefix: str, ncols: int) -> None:
        self._actor = actor
        self._id = line_id
        self._prefix = prefix
        self._ncols = ncols
        self._cached_message = ""

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, value: str) -> None:
        self._prefix = value
        self._ncols = self._actor.terminal_width - len(_remove_escape_sequences(value))
        self._actor.send(("set_prefix", self._id, value))

    @property
    def ncols(self) -> int:
        return self._ncols

    @property
    def message(self) -> str:
        return self._cached_message

    @message.setter
    def message(self, value: str) -> None:
        self.update(value)

    def update(self, message: str) -> None:
        assert "\t" not in message, "Tab is not allowed in Line"
        self._cached_message = message
        self._actor.send(("update", self._id, message))

    def flush(self) -> None:
        self._actor.send(("flush", self._id))

    def add_subline(self, prefix: str = "") -> "Line":
        return self._actor._create_subline(parent_id=self._id, prefix=prefix)

    def remove_subline(self, line: "Line") -> None:
        self._actor.send(("remove_subline", self._id, line._id))


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------

class ParallaxPrinter(Actor):
    """Actor that manages a dynamic set of terminal lines.

    Rendering and state mutation happen exclusively on the actor thread.
    """

    out: IO[str]
    terminal_width: int
    terminal_height: int

    _lines: dict[int, _LineState]
    _root_order: list[int]
    _next_id: int
    _id_lock: threading.Lock
    _needs_render: bool
    _last_flush_ncols: int

    def __init__(
        self,
        nlines: int = 0,
        out: IO[str] = sys.stdout,
        disable_stdin: bool = True,
        root_prefix: str = "",
    ) -> None:
        self.out = out
        self.terminal_width, self.terminal_height = self._get_terminal_size()
        self._lines = {}
        self._root_order = []
        self._next_id = 0
        self._id_lock = threading.Lock()
        self._needs_render = False
        self._last_flush_ncols = 0
        self._initial_lines: list[Line] = []

        for _ in range(nlines):
            self._initial_lines.append(self._add_line_sync(prefix=root_prefix))

        if disable_stdin:
            self._disable_stdin()

        super().__init__()

    # -- public API (any thread) --------------------------------------------

    def __getitem__(self, lineno: int) -> Line:
        return self._initial_lines[lineno]

    def line(self, lineno: int) -> Line:
        return self._initial_lines[lineno]

    def add_line(self, prefix: str = "") -> Line:
        line_id = self._alloc_id()
        ncols = self.terminal_width - len(_remove_escape_sequences(prefix))
        self.send(("add_line", line_id, prefix))
        handle = Line(actor=self, line_id=line_id, prefix=prefix, ncols=ncols)
        return handle

    def remove_line(self, line: Line) -> None:
        self.send(("remove_line", line._id))

    def terminate(self) -> None:
        self.send(("terminate",))
        self._thread.join(timeout=2.0)

    # -- internal -----------------------------------------------------------

    def _add_line_sync(self, prefix: str) -> Line:
        """Create a root line during __init__ (before actor thread starts)."""
        line_id = self._alloc_id()
        self._lines[line_id] = _LineState(prefix=prefix, parent_id=None)
        self._root_order.append(line_id)
        ncols = self.terminal_width - len(_remove_escape_sequences(prefix))
        return Line(actor=self, line_id=line_id, prefix=prefix, ncols=ncols)

    def _create_subline(self, parent_id: int, prefix: str) -> Line:
        line_id = self._alloc_id()
        ncols = self.terminal_width - len(_remove_escape_sequences(prefix))
        self.send(("add_subline", parent_id, line_id, prefix))
        return Line(actor=self, line_id=line_id, prefix=prefix, ncols=ncols)

    def _alloc_id(self) -> int:
        with self._id_lock:
            lid = self._next_id
            self._next_id += 1
            return lid

    @staticmethod
    def _disable_stdin() -> None:
        try:
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            pass

    # -- actor callbacks (actor thread only) --------------------------------

    def receive(self, message: Any) -> None:
        tag = message[0]

        if tag == "update":
            _, line_id, text = message
            if line_id in self._lines:
                self._lines[line_id].message = text
                self._needs_render = True

        elif tag == "set_prefix":
            _, line_id, prefix = message
            if line_id in self._lines:
                self._lines[line_id].prefix = prefix
                self._needs_render = True

        elif tag == "flush":
            self._needs_render = True

        elif tag == "add_line":
            _, line_id, prefix = message
            self._lines[line_id] = _LineState(prefix=prefix, parent_id=None)
            self._root_order.append(line_id)
            self._needs_render = True

        elif tag == "add_subline":
            _, parent_id, line_id, prefix = message
            self._lines[line_id] = _LineState(prefix=prefix, parent_id=parent_id)
            if parent_id in self._lines:
                self._lines[parent_id].children.append(line_id)
            self._needs_render = True

        elif tag == "remove_subline":
            _, parent_id, child_id = message
            if parent_id in self._lines:
                children = self._lines[parent_id].children
                if child_id in children:
                    children.remove(child_id)
            self._remove_tree(child_id)
            self._needs_render = True

        elif tag == "remove_line":
            _, line_id = message
            if line_id in self._root_order:
                self._root_order.remove(line_id)
            self._remove_tree(line_id)
            self._needs_render = True

        elif tag == "terminate":
            self._stop_event.set()

    def _remove_tree(self, line_id: int) -> None:
        if line_id not in self._lines:
            return
        for child_id in self._lines[line_id].children:
            self._remove_tree(child_id)
        del self._lines[line_id]

    def after_receive(self) -> None:
        if self._needs_render:
            self._render()
            self._needs_render = False

    # -- rendering (actor thread only) --------------------------------------

    def _format_line(self, line_id: int) -> str:
        state = self._lines[line_id]
        result = state.prefix + state.message
        for child_id in state.children:
            if child_id in self._lines:
                result += '\n' + self._format_line(child_id)
        return result

    def _render(self) -> None:
        res = ""
        if self._last_flush_ncols != 0:
            res += '\033[1G' + '\033[A' * self._last_flush_ncols + '\033[0J'

        self._last_flush_ncols = 0
        for line_id in self._root_order:
            if line_id not in self._lines:
                continue
            text = self._format_line(line_id)
            delta = self._lines_in_terminal(text)
            if self._last_flush_ncols + delta >= self.terminal_height - 1:
                res += "...\n"
                self._last_flush_ncols += 2
                break
            self._last_flush_ncols += delta
            res += text + '\n'

        self.out.write(res)
        self.out.flush()

    # -- terminal geometry helpers ------------------------------------------

    def _lines_in_terminal(self, text: str) -> int:
        text = _remove_escape_sequences(text)
        total = 0
        for line in text.split('\n'):
            factor = 1
            col = 0
            for ch in line:
                w = 2 if unicodedata.east_asian_width(ch) in 'FW' else 1
                col += w
                if col > self.terminal_width:
                    col = w
                    factor += 1
            total += factor
        return total

    @staticmethod
    def _get_terminal_size() -> tuple[int, int]:
        try:
            size = shutil.get_terminal_size()
            return size.columns, size.lines
        except AttributeError:
            return 80, 24
