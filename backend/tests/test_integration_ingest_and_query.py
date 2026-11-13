"""End-to-end: ingest a real StatsBomb match, then read it back through
the public players API."""

import json
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.main import app
from app.models.base import Base
from app.services.ingestion.statsbomb_ingestion_service import ingest_match

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "statsbomb"

COMPETITION = {
    "statsbomb_competition_id": 43,
    "name": "FIFA World Cup",
    "country": "International",
    "gender": "male",
}
SEASON = {"statsbomb_season_id": 106, "name": "2022"}

# The real StatsBomb matches/43/106.json entry for 3857276, reduced to the
# fields ingest_match reads.
MATCH_JSON = {
    "match_id": 3857276,
    "match_date": "2022-12-01",
    "home_team": {
        "home_team_id": 1833,
        "home_team_name": "Canada",
        "country": {"id": 40, "name": "Canada"},
    },
    "away_team": {
        "away_team_id": 788,
        "away_team_name": "Morocco",
        "country": {"id": 154, "name": "Morocco"},
    },
    "home_score": 1,
    "away_score": 2,
}


def _load_fixture(name: str) -> list[dict]:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_ingested_players_are_served_by_players_api(
    client: TestClient, session: Session
) -> None:
    lineups_json = _load_fixture("lineups_3857276.json")
    ingest_match(
        session=session,
        competition=COMPETITION,
        season=SEASON,
        match_json=MATCH_JSON,
        lineups_json=lineups_json,
        events_json=_load_fixture("events_3857276.json"),
    )
    session.commit()

    response = client.get("/api/v1/players", params={"limit": 200})
    assert response.status_code == 200
    players = response.json()

    total_lineup_players = sum(len(team["lineup"]) for team in lineups_json)
    assert len(players) == total_lineup_players

    by_name = {p["name"]: p for p in players}
    en_nesyri = by_name["Youssef En-Nesyri"]
    assert en_nesyri["nationality"] == "Morocco"
    assert en_nesyri["primary_position"] == "Center Forward"

    detail = client.get(f"/api/v1/players/{en_nesyri['id']}")
    assert detail.status_code == 200
    assert detail.json() == en_nesyri
