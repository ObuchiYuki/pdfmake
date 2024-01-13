from typing import Callable, Any, TypeVar

import threading

Argument = TypeVar("Argument")

class ParallaxExecutor:
    max_parallel: int
    queue: list[
        tuple[
            Callable[[Any], None],
            Any
        ]
    ]
    current_parallel: int
    threads: set[threading.Thread] = set()

    def __init__(self, max_workers: int = 4) -> None:
        self.max_parallel = max_workers
        self.queue = []
        self.current_parallel = 0

    def register(self, block: Callable[[Argument], None], arg: Argument = None):
        self.queue.append((block, arg))
        self._run()

    def join(self):
        while len(self.threads) > 0:
            self.threads.pop().join()

    def _run(self):
        if self.current_parallel >= self.max_parallel:
            return

        if len(self.queue) == 0:
            return

        self.current_parallel += 1
        block = self.queue.pop(0)
        thread = threading.Thread(target=self._run_block, args=(block,))
        thread.daemon = True
        thread.start()
        self.threads.add(thread)

    def _run_block(self, block: tuple[Callable[[Any], None], Any]):
        block[0](block[1])
        self.current_parallel -= 1
        self._run()
