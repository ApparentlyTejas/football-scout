import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.match import Match
from app.models.player import Player
from app.models.player_match_stat import PlayerMatchStat
from app.services.ingestion.statsbomb_ingestion_service import ingest_match

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "statsbomb"


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


COMPETITION = {
    "statsbomb_competition_id": 43,
    "name": "FIFA World Cup",
    "country": "International",
    "gender": "male",
}

SEASON = {
    "statsbomb_season_id": 106,
    "name": "2022",
}

MATCH_JSON = {
    "match_id": 3857276,
    "match_date": "2022-12-01",
    "home_team": {"home_team_id": 788, "home_team_name": "Morocco"},
    "away_team": {"away_team_id": 1833, "away_team_name": "Canada"},
    "home_score": 2,
    "away_score": 1,
}


def _stat_for_player_name(session: Session, lineups_json: list[dict], name: str) -> PlayerMatchStat:
    players_by_name = {p.name: p for p in session.execute(select(Player)).scalars().all()}
    player = players_by_name[name]
    return session.execute(
        select(PlayerMatchStat).where(PlayerMatchStat.player_id == player.id)
    ).scalar_one()


def test_ingest_match_creates_expected_rows(session: Session) -> None:
    lineups_json = _load_fixture("lineups_3857276.json")
    events_json = _load_fixture("events_3857276.json")

    match = ingest_match(
        session=session,
        competition=COMPETITION,
        season=SEASON,
        match_json=MATCH_JSON,
        lineups_json=lineups_json,
        events_json=events_json,
    )
    session.commit()

    matches = session.execute(select(Match)).scalars().all()
    assert len(matches) == 1
    assert matches[0].statsbomb_match_id == 3857276
    assert match.statsbomb_match_id == 3857276

    total_lineup_players = sum(len(team["lineup"]) for team in lineups_json)

    players = session.execute(select(Player)).scalars().all()
    assert len(players) == total_lineup_players

    stats = session.execute(select(PlayerMatchStat)).scalars().all()
    assert len(stats) == total_lineup_players

    en_nesyri = _stat_for_player_name(session, lineups_json, "Youssef En-Nesyri")

    assert en_nesyri.match_id == match.id
    assert en_nesyri.passes_attempted == 18
    assert en_nesyri.passes_completed == 12
    assert en_nesyri.shots == 2
    assert en_nesyri.duels == 4
    assert en_nesyri.aerial_duels == 6
    assert en_nesyri.interceptions == 0
    assert en_nesyri.carries == 21
    assert en_nesyri.pressures == 16
    assert en_nesyri.ball_recoveries == 4
    assert en_nesyri.dribbles == 4
    assert en_nesyri.dispossessed == 0
    assert en_nesyri.miscontrols == 3
    # Open-ended until the real final whistle at 93:54 (from events_json),
    # rounded to the Integer column.
    assert en_nesyri.minutes_played == 94


def test_ingest_match_is_idempotent(session: Session) -> None:
    lineups_json = _load_fixture("lineups_3857276.json")
    events_json = _load_fixture("events_3857276.json")

    ingest_match(
        session=session,
        competition=COMPETITION,
        season=SEASON,
        match_json=MATCH_JSON,
        lineups_json=lineups_json,
        events_json=events_json,
    )
    session.commit()

    counts_first = {
        "matches": len(session.execute(select(Match)).scalars().all()),
        "players": len(session.execute(select(Player)).scalars().all()),
        "stats": len(session.execute(select(PlayerMatchStat)).scalars().all()),
    }

    ingest_match(
        session=session,
        competition=COMPETITION,
        season=SEASON,
        match_json=MATCH_JSON,
        lineups_json=lineups_json,
        events_json=events_json,
    )
    session.commit()

    counts_second = {
        "matches": len(session.execute(select(Match)).scalars().all()),
        "players": len(session.execute(select(Player)).scalars().all()),
        "stats": len(session.execute(select(PlayerMatchStat)).scalars().all()),
    }

    assert counts_first == counts_second


def test_player_with_zero_events_still_gets_a_stats_row(session: Session) -> None:
    lineups_json = _load_fixture("lineups_3857276.json")
    events_json = _load_fixture("events_3857276.json")

    # Pick a lineup player who has no entries in the trimmed events fixture
    # (the fixture only carries events for players 6301 and 3625).
    zero_event_player_name = None
    for team in lineups_json:
        for player in team["lineup"]:
            if player["player_id"] not in (6301, 3625):
                zero_event_player_name = player["player_name"]
                break
        if zero_event_player_name:
            break
    assert zero_event_player_name is not None

    match = ingest_match(
        session=session,
        competition=COMPETITION,
        season=SEASON,
        match_json=MATCH_JSON,
        lineups_json=lineups_json,
        events_json=events_json,
    )
    session.commit()

    stat = _stat_for_player_name(session, lineups_json, zero_event_player_name)

    assert stat.match_id == match.id
    assert stat.passes_attempted == 0
    assert stat.passes_completed == 0
    assert stat.shots == 0
    assert stat.carries == 0
    assert stat.pressures == 0
    assert stat.interceptions == 0
    assert stat.ball_recoveries == 0
    assert stat.dribbles == 0
    assert stat.duels == 0
    assert stat.aerial_duels == 0
    assert stat.dispossessed == 0
    assert stat.miscontrols == 0
    assert stat.minutes_played is not None


def test_ingest_match_sets_primary_position(session: Session) -> None:
    lineups_json = _load_fixture("lineups_3857276.json")
    events_json = _load_fixture("events_3857276.json")

    ingest_match(
        session=session,
        competition=COMPETITION,
        season=SEASON,
        match_json=MATCH_JSON,
        lineups_json=lineups_json,
        events_json=events_json,
    )
    session.commit()

    players_by_name = {p.name: p for p in session.execute(select(Player)).scalars().all()}
    assert players_by_name["Youssef En-Nesyri"].primary_position == "Center Forward"
    assert players_by_name["Sofiane Boufal"].primary_position == "Left Wing"

    # Re-ingesting data that lacks position records for En-Nesyri must
    # not wipe the position already stored.
    stripped = copy.deepcopy(lineups_json)
    for team in stripped:
        for player in team["lineup"]:
            if player["player_id"] == 6301:
                player["positions"] = []

    ingest_match(
        session=session,
        competition=COMPETITION,
        season=SEASON,
        match_json=MATCH_JSON,
        lineups_json=stripped,
        events_json=events_json,
    )
    session.commit()

    en_nesyri = session.execute(
        select(Player).where(Player.name == "Youssef En-Nesyri")
    ).scalar_one()
    assert en_nesyri.primary_position == "Center Forward"
