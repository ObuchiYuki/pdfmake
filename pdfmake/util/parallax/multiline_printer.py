#
# multiline_printer.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

"""
Actor-based multi-line terminal printer with tqdm integration.

All mutable display state lives inside the MultilinePrinter actor.
SingleLinePrinter is a lightweight handle that sends messages; it
never reads or writes shared state directly.

Usage:
    printer = MultilinePrinter(ncols=2)
    p0 = printer.printer(0)
    p1 = printer.printer(1)

    for i in tqdm(range(100), **p0.tqdm_wrapper()):
        p1.print(f"i: {i}")
"""

import tty
from typing import IO, Any
import sys
import shutil
import unicodedata

from pdfmake.util.remove_escape_sequences import remove_escape_sequences
from pdfmake.util.parallax.actor import Actor


# ---------------------------------------------------------------------------
# Internal line state (only touched by the actor thread)
# ---------------------------------------------------------------------------

class _LineState:
    __slots__ = ("prefix", "message", "parent_id", "ncol_slot", "children")

    def __init__(self, prefix: str, parent_id: int | None, ncol_slot: int | None) -> None:
        self.prefix = prefix
        self.message = ""
        self.parent_id = parent_id
        self.ncol_slot = ncol_slot
        self.children: list[int] = []


# ---------------------------------------------------------------------------
# tqdm adapter
# ---------------------------------------------------------------------------

class _TqdmAdapter:
    """Adapts SingleLinePrinter to tqdm's file= interface."""

    def __init__(self, handle: "SingleLinePrinter") -> None:
        self._handle = handle

    def write(self, text: str) -> None:
        text = remove_escape_sequences(text).replace('\r', '').replace('\n', '')
        if text:
            self._handle.print(text)

    def flush(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Handle (thread-safe, sends messages only)
# ---------------------------------------------------------------------------

class SingleLinePrinter:
    """Thread-safe handle to one line inside a MultilinePrinter actor."""

    _actor: "MultilinePrinter"
    _id: int
    _ncols: int
    _prefix: str

    def __init__(self, actor: "MultilinePrinter", line_id: int, prefix: str, ncols: int) -> None:
        self._actor = actor
        self._id = line_id
        self._prefix = prefix
        self._ncols = ncols

    @property
    def ncols(self) -> int:
        return self._ncols

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, value: str) -> None:
        self._prefix = value
        self._ncols = self._actor.terminal_width - len(remove_escape_sequences(value))
        self._actor.send(("set_prefix", self._id, value))

    def print(self, message: str) -> None:
        assert "\t" not in message, "Tab is not allowed in SingleLinePrinter"
        self._actor.send(("update", self._id, message))

    def flush(self) -> None:
        self._actor.send(("flush", self._id))

    def subprinter(self, prefix: str = "") -> "SingleLinePrinter":
        return self._actor._create_subline(self._id, prefix)

    def tqdm_wrapper(self) -> dict:
        return {"file": _TqdmAdapter(self), "ncols": self._ncols, "ascii": False}


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------

class MultilinePrinter(Actor):
    """Actor that owns all line state and serializes terminal rendering.

    Worker threads interact exclusively through SingleLinePrinter handles
    which send messages to this actor's mailbox.  The actor thread is the
    only one that reads state or writes to the terminal.
    """

    ncols: int
    out: IO[str]
    terminal_width: int

    _lines: dict[int, _LineState]
    _ncol_slots: list[int]
    _root_printers: list[SingleLinePrinter]
    _next_id: int
    _needs_render: bool
    _already_printed: bool
    _line_flushed: int

    def __init__(
        self,
        ncols: int,
        out: IO[str] = sys.stdout,
        disable_input: bool = True,
        root_prefix: str = "",
    ) -> None:
        self.ncols = ncols
        self.out = out
        self.terminal_width = self._get_width()
        self._lines = {}
        self._ncol_slots = []
        self._root_printers = []
        self._next_id = 0
        self._needs_render = False
        self._already_printed = False
        self._line_flushed = 0

        prefix_display_len = len(remove_escape_sequences(root_prefix))
        for i in range(ncols):
            line_id = self._alloc_id()
            self._lines[line_id] = _LineState(prefix=root_prefix, parent_id=None, ncol_slot=i)
            self._ncol_slots.append(line_id)
            self._root_printers.append(SingleLinePrinter(
                actor=self,
                line_id=line_id,
                prefix=root_prefix,
                ncols=self.terminal_width - prefix_display_len,
            ))

        if disable_input:
            try:
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                pass

        super().__init__()

    # -- public API (called from any thread) --------------------------------

    def printer(self, line: int) -> SingleLinePrinter:
        assert line < self.ncols, "line index out of range"
        return self._root_printers[line]

    def terminate(self) -> None:
        self.send(("terminate",))
        self._thread.join(timeout=2.0)

    # -- internal (called from main thread during setup) --------------------

    def _create_subline(self, parent_id: int, prefix: str) -> SingleLinePrinter:
        line_id = self._alloc_id()
        ncols = self.terminal_width - len(remove_escape_sequences(prefix))
        self.send(("register_subline", line_id, parent_id, prefix))
        return SingleLinePrinter(actor=self, line_id=line_id, prefix=prefix, ncols=ncols)

    def _alloc_id(self) -> int:
        lid = self._next_id
        self._next_id += 1
        return lid

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

        elif tag == "register_subline":
            _, line_id, parent_id, prefix = message
            self._lines[line_id] = _LineState(prefix=prefix, parent_id=parent_id, ncol_slot=None)
            if parent_id in self._lines:
                self._lines[parent_id].children.append(line_id)

        elif tag == "terminate":
            self._stop_event.set()

    def after_receive(self) -> None:
        if self._needs_render:
            self._render()
            self._needs_render = False

    # -- rendering (actor thread only) --------------------------------------

    def _format_line(self, line_id: int) -> str:
        state = self._lines[line_id]
        result = state.prefix + state.message
        for child_id in state.children:
            result += '\n' + self._format_line(child_id)
        return result

    def _render(self) -> None:
        head = self._erase_print_area() if self._already_printed else ""

        self._line_flushed = 0
        body = ""
        for slot_id in self._ncol_slots:
            text = self._format_line(slot_id)
            self._line_flushed += self._lines_in_terminal(text)
            body += text + '\n'

        self.out.write(head + body)
        self.out.flush()
        self._already_printed = True

    def _erase_print_area(self) -> str:
        if self._line_flushed == 0:
            return ""
        return '\033[1G' + '\033[A' * self._line_flushed + '\033[0J'

    # -- terminal geometry helpers ------------------------------------------

    @staticmethod
    def _get_width() -> int:
        try:
            return shutil.get_terminal_size().columns
        except AttributeError:
            return 80

    def _lines_in_terminal(self, text: str) -> int:
        text = remove_escape_sequences(text)
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
