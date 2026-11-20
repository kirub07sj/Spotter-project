import httpx
import pytest
import respx

from planner.domain.errors import ProviderUnavailableError
from planner.providers.http import HttpClient

URL = "https://example.test/x"


@respx.mock
async def test_retries_5xx_then_succeeds(http: HttpClient, sleeps: list[float]) -> None:
    route = respx.get(URL).mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )
    assert await http.get_json(URL, {}, provider="t") == (200, {"ok": True})
    assert route.call_count == 2
    assert len(sleeps) == 1 and 0.3 <= sleeps[0] <= 0.375  # backoff 0.3 s plus jitter


@respx.mock
async def test_gives_up_after_two_retries(http: HttpClient, sleeps: list[float]) -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(500))
    with pytest.raises(ProviderUnavailableError):
        await http.get_json(URL, {}, provider="t")
    assert route.call_count == 3
    assert 0.9 <= sleeps[1] <= 1.125


@respx.mock
async def test_timeouts_are_retried(http: HttpClient) -> None:
    respx.get(URL).mock(side_effect=[httpx.ReadTimeout("slow"), httpx.Response(200, json=[1])])
    assert await http.get_json(URL, {}, provider="t") == (200, [1])


@respx.mock
async def test_429_honours_retry_after(http: HttpClient, sleeps: list[float]) -> None:
    respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(429, headers={"Retry-After": "soon"}),  # unparseable: backoff
            httpx.Response(200, json={}),
        ]
    )
    await http.get_json(URL, {}, provider="t")
    assert sleeps[0] == 2.0
    assert 0.9 <= sleeps[1] <= 1.125


@respx.mock
async def test_retry_after_is_capped(http: HttpClient, sleeps: list[float]) -> None:
    respx.get(URL).mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "600"}), httpx.Response(200)]
    )
    assert await http.get_json(URL, {}, provider="t") == (200, None)  # non-JSON body
    assert sleeps == [3.0]


@respx.mock
async def test_4xx_is_returned_not_retried(http: HttpClient) -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(422, json={"code": "InvalidInput"}))
    assert await http.get_json(URL, {}, provider="t") == (422, {"code": "InvalidInput"})
    assert route.call_count == 1


async def test_shared_client_is_reused_per_loop() -> None:
    a, b = HttpClient(), HttpClient()
    original = a.client
    assert original is b.client
    await original.aclose()
    replacement = HttpClient().client
    assert replacement is not original  # a closed client is replaced
    await replacement.aclose()
