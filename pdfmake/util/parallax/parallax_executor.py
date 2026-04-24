#
# parallax_executor.py
# pdfmake
#
# Created by Yuki Obuchi on 04/24/26.
# Copyright © 2026 X Corp. All rights reserved.
#

"""Thread pool executor backed by concurrent.futures."""

from typing import Callable, Any, TypeVar
from concurrent.futures import ThreadPoolExecutor, Future

Argument = TypeVar("Argument")


class ParallaxExecutor:
    """Submit tasks to a bounded thread pool.

    max_workers can be set before the first register() call.
    The underlying ThreadPoolExecutor is created lazily so that
    max_workers can be adjusted after construction.
    """

    max_workers: int

    _executor: ThreadPoolExecutor | None
    _futures: list[Future[None]]

    def __init__(self, daemon: bool = True, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self._daemon = daemon
        self._executor = None
        self._futures = []

    def register(self, block: Callable[[Argument], None], arg: Argument = None) -> None:  # type: ignore[assignment]
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._futures.append(self._executor.submit(block, arg))

    def join(self) -> None:
        """Wait for all submitted tasks to complete."""
        for f in self._futures:
            f.result()
        self.shutdown()

    def shutdown(self, wait: bool = True) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None
