"""Collects stage durations for the Server-Timing header (docs/02 §9)."""

import time
from collections.abc import Iterator
from contextlib import contextmanager


class Timings:
    def __init__(self) -> None:
        self.ms: dict[str, float] = {}

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            self.ms[name] = self.ms.get(name, 0.0) + elapsed

    def header(self) -> str:
        return ", ".join(f"{name};dur={ms:.1f}" for name, ms in self.ms.items())
