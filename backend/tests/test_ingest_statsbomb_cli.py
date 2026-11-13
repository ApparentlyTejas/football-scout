import importlib.util
import json
from pathlib import Path

import pytest
import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.match import Match
from app.services.ingestion.statsbomb_client import StatsBombFetchError

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "statsbomb"
SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ingest" / "ingest_statsbomb.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ingest_statsbomb", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ingest_statsbomb = _load_module()


def _load_fixture(name: str) -> list[dict]:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


COMPETITION_ENTRY = {
    "competition_id": 43,
    "season_id": 106,
    "country_name": "International",
    "competition_name": "FIFA World Cup",
    "competition_gender": "male",
    "season_name": "2022",
}


def _match_stub(match_id: int) -> dict:
    return {
        "match_id": match_id,
        "match_date": "2022-12-01",
        "home_team": {"home_team_id": 788, "home_team_name": "Morocco"},
        "away_team": {"away_team_id": 1833, "away_team_name": "Canada"},
        "home_score": 2,
        "away_score": 1,
    }


REAL_MATCH_ID = 3857276


def test_run_ingestion_continues_after_one_match_fetch_fails(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    lineups_json = _load_fixture("lineups_3857276.json")
    events_json = _load_fixture("events_3857276.json")

    failing_match_id = 999999
    match_stubs = [_match_stub(failing_match_id), _match_stub(REAL_MATCH_ID)]

    monkeypatch.setattr(
        ingest_statsbomb, "fetch_competitions", lambda: [COMPETITION_ENTRY]
    )
    monkeypatch.setattr(
        ingest_statsbomb, "fetch_matches", lambda competition_id, season_id: match_stubs
    )

    def fake_fetch_lineups(match_id: int) -> list[dict]:
        if match_id == failing_match_id:
            raise StatsBombFetchError("boom")
        return lineups_json

    def fake_fetch_events(match_id: int) -> list[dict]:
        if match_id == failing_match_id:
            raise StatsBombFetchError("boom")
        return events_json

    monkeypatch.setattr(ingest_statsbomb, "fetch_lineups", fake_fetch_lineups)
    monkeypatch.setattr(ingest_statsbomb, "fetch_events", fake_fetch_events)

    summary = ingest_statsbomb.run_ingestion(
        session, competition_id=43, season_id=106
    )
    session.commit()

    assert summary.matches_attempted == 2
    assert summary.matches_failed == 1
    assert summary.matches_ingested == 1

    matches = session.execute(select(Match)).scalars().all()
    assert len(matches) == 1
    assert matches[0].statsbomb_match_id == REAL_MATCH_ID


def test_run_ingestion_respects_limit(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    match_stubs = [_match_stub(match_id) for match_id in range(1, 6)]

    monkeypatch.setattr(
        ingest_statsbomb, "fetch_competitions", lambda: [COMPETITION_ENTRY]
    )
    monkeypatch.setattr(
        ingest_statsbomb, "fetch_matches", lambda competition_id, season_id: match_stubs
    )
    monkeypatch.setattr(ingest_statsbomb, "fetch_lineups", lambda match_id: [])
    monkeypatch.setattr(ingest_statsbomb, "fetch_events", lambda match_id: [])

    summary = ingest_statsbomb.run_ingestion(
        session, competition_id=43, season_id=106, limit=2
    )
    session.commit()

    assert summary.matches_attempted == 2


def test_run_ingestion_counts_network_error_as_per_match_failure(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ConnectionError raised by `requests` inside the real fetch layer
    (not a monkeypatched fetch_* function) must be counted as one failed
    match, not abort the whole run."""
    lineups_json = _load_fixture("lineups_3857276.json")
    events_json = _load_fixture("events_3857276.json")

    failing_match_id = 999999
    match_stubs = [_match_stub(failing_match_id), _match_stub(REAL_MATCH_ID)]

    monkeypatch.setattr(
        ingest_statsbomb, "fetch_competitions", lambda: [COMPETITION_ENTRY]
    )
    monkeypatch.setattr(
        ingest_statsbomb, "fetch_matches", lambda competition_id, season_id: match_stubs
    )

    class FakeResponse:
        status_code = 200

        def __init__(self, payload: list[dict]) -> None:
            self._payload = payload

        def json(self) -> list[dict]:
            return self._payload

    def fake_get(url: str, timeout: float) -> FakeResponse:
        if f"/{failing_match_id}.json" in url:
            raise requests.exceptions.ConnectionError("connection reset")
        if "/lineups/" in url:
            return FakeResponse(lineups_json)
        return FakeResponse(events_json)

    monkeypatch.setattr(requests, "get", fake_get)

    summary = ingest_statsbomb.run_ingestion(
        session, competition_id=43, season_id=106
    )
    session.commit()

    assert summary.matches_attempted == 2
    assert summary.matches_failed == 1
    assert summary.matches_ingested == 1

    matches = session.execute(select(Match)).scalars().all()
    assert [m.statsbomb_match_id for m in matches] == [REAL_MATCH_ID]
