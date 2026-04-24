#
# actor.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

"""
Base actor: serial message processing on a dedicated thread.

Subclass and override receive(). Call send() from any thread.
Messages are drained in batches; after_receive() is called once
per batch for efficient bulk updates (e.g. a single re-render
after multiple state changes).
"""

import queue
import threading
from typing import Any


class Actor:

    _mailbox: queue.Queue[Any]
    _stop_event: threading.Event
    _thread: threading.Thread

    def __init__(self) -> None:
        self._mailbox = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def send(self, message: Any) -> None:
        """Enqueue a message for the actor thread (thread-safe)."""
        self._mailbox.put(message)

    def receive(self, message: Any) -> None:
        """Handle one message on the actor thread. Override in subclass."""

    def after_receive(self) -> None:
        """Called once after each drained batch. Override for bulk side-effects."""

    def _run_loop(self) -> None:
        while not self._stop_event.is_set() or not self._mailbox.empty():
            batch = self._drain()
            if not batch:
                continue
            for msg in batch:
                self.receive(msg)
            self.after_receive()

    def _drain(self) -> list[Any]:
        result: list[Any] = []
        try:
            result.append(self._mailbox.get(timeout=0.05))
            while True:
                try:
                    result.append(self._mailbox.get_nowait())
                except queue.Empty:
                    break
        except queue.Empty:
            pass
        return result
