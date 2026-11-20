import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from planner.providers.http import HttpClient

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load(rel: str) -> Any:
    return json.loads((FIXTURES / rel).read_text())


@pytest.fixture
def load_fixture() -> Callable[[str], Any]:
    return load


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def http(sleeps: list[float]) -> HttpClient:
    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    # A dedicated client per test; respx intercepts it, pytest-socket blocks real sockets.
    return HttpClient(sleep=fake_sleep, client=httpx.AsyncClient(timeout=8.0))
