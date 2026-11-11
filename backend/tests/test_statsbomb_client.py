import pytest
import requests

from app.services.ingestion import statsbomb_client
from app.services.ingestion.statsbomb_client import (
    BASE_URL,
    StatsBombFetchError,
    fetch_events,
    fetch_matches,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: object = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


def test_fetch_matches_builds_correct_url_and_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> FakeResponse:
        assert url == f"{BASE_URL}/matches/43/106.json"
        return FakeResponse(200, [{"match_id": 1}])

    monkeypatch.setattr(requests, "get", fake_get)

    assert fetch_matches(43, 106) == [{"match_id": 1}]


def test_fetch_events_raises_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> FakeResponse:
        return FakeResponse(404)

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(StatsBombFetchError):
        fetch_events(999999)
