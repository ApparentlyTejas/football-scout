import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.competition import Competition
from app.models.match import Match
from app.models.player import Player
from app.models.player_match_stat import PlayerMatchStat
from app.models.season import Season
from app.models.team import Team
from app.services.features.season_aggregator import aggregate_season


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


def _make_season(session: Session) -> Season:
    competition = Competition(
        statsbomb_competition_id=43, name="FIFA World Cup", country="International", gender="male"
    )
    session.add(competition)
    session.flush()
    season = Season(competition_id=competition.id, statsbomb_season_id=106, name="2022")
    session.add(season)
    session.flush()
    return season


def _make_match(session: Session, season_id: int, home_team_id: int, away_team_id: int, statsbomb_match_id: int) -> Match:
    match = Match(
        statsbomb_match_id=statsbomb_match_id,
        season_id=season_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        match_date=datetime.date(2022, 11, 20 + statsbomb_match_id),
        home_score=1,
        away_score=0,
    )
    session.add(match)
    session.flush()
    return match


def test_aggregate_season_sums_stats_and_computes_per_90(session: Session) -> None:
    season = _make_season(session)
    team = Team(name="Morocco", country="Morocco")
    opponent = Team(name="France", country="France")
    session.add_all([team, opponent])
    session.flush()

    player = Player(name="Youssef En-Nesyri", primary_position="Center Forward")
    session.add(player)
    session.flush()

    match1 = _make_match(session, season.id, team.id, opponent.id, 1)
    match2 = _make_match(session, season.id, team.id, opponent.id, 2)

    session.add_all(
        [
            PlayerMatchStat(
                player_id=player.id,
                match_id=match1.id,
                team_id=team.id,
                minutes_played=45,
                passes_attempted=10,
                passes_completed=8,
                shots=2,
                carries=5,
                pressures=3,
                interceptions=1,
                ball_recoveries=2,
                dribbles=1,
                duels=2,
                aerial_duels=1,
                dispossessed=1,
                miscontrols=0,
            ),
            PlayerMatchStat(
                player_id=player.id,
                match_id=match2.id,
                team_id=team.id,
                minutes_played=45,
                passes_attempted=10,
                passes_completed=9,
                shots=1,
                carries=5,
                pressures=3,
                interceptions=1,
                ball_recoveries=2,
                dribbles=1,
                duels=2,
                aerial_duels=1,
                dispossessed=1,
                miscontrols=0,
            ),
        ]
    )
    session.commit()

    results = aggregate_season(session, season.id)

    assert len(results) == 1
    result = results[0]
    assert result.player_id == player.id
    assert result.matches_played == 2
    assert result.minutes_played == 90
    assert result.shots == 3
    assert result.shots_per_90 == 3.0
    assert result.passes_attempted == 20
    assert result.passes_completed == 17
    assert result.pass_completion_pct == 85.0
    assert result.position_group == "FW"


def test_aggregate_season_handles_zero_minutes_player(session: Session) -> None:
    season = _make_season(session)
    team = Team(name="Morocco", country="Morocco")
    opponent = Team(name="France", country="France")
    session.add_all([team, opponent])
    session.flush()

    player = Player(name="Unused Substitute", primary_position="Right Back")
    session.add(player)
    session.flush()

    match = _make_match(session, season.id, team.id, opponent.id, 1)
    session.add(
        PlayerMatchStat(
            player_id=player.id,
            match_id=match.id,
            team_id=team.id,
            minutes_played=0,
            passes_attempted=0,
            passes_completed=0,
            shots=0,
            carries=0,
            pressures=0,
            interceptions=0,
            ball_recoveries=0,
            dribbles=0,
            duels=0,
            aerial_duels=0,
            dispossessed=0,
            miscontrols=0,
        )
    )
    session.commit()

    results = aggregate_season(session, season.id)

    assert len(results) == 1
    result = results[0]
    assert result.matches_played == 0
    assert result.minutes_played == 0
    assert result.pass_completion_pct is None
    assert result.passes_per_90 is None
    assert result.shots_per_90 is None
    assert result.carries_per_90 is None
    assert result.pressures_per_90 is None
    assert result.interceptions_per_90 is None
    assert result.ball_recoveries_per_90 is None
    assert result.dribbles_per_90 is None
    assert result.duels_per_90 is None
    assert result.aerial_duels_per_90 is None
    assert result.dispossessed_per_90 is None
    assert result.miscontrols_per_90 is None


def test_aggregate_season_excludes_bench_matches_from_matches_played(session: Session) -> None:
    season = _make_season(session)
    team = Team(name="Morocco", country="Morocco")
    opponent = Team(name="France", country="France")
    session.add_all([team, opponent])
    session.flush()

    player = Player(name="Squad Player", primary_position="Right Back")
    session.add(player)
    session.flush()

    played_match = _make_match(session, season.id, team.id, opponent.id, 1)
    bench_match = _make_match(session, season.id, team.id, opponent.id, 2)

    session.add_all(
        [
            PlayerMatchStat(
                player_id=player.id,
                match_id=played_match.id,
                team_id=team.id,
                minutes_played=90,
                passes_attempted=10,
                passes_completed=8,
                shots=0,
                carries=0,
                pressures=0,
                interceptions=0,
                ball_recoveries=0,
                dribbles=0,
                duels=0,
                aerial_duels=0,
                dispossessed=0,
                miscontrols=0,
            ),
            PlayerMatchStat(
                player_id=player.id,
                match_id=bench_match.id,
                team_id=team.id,
                minutes_played=0,
                passes_attempted=0,
                passes_completed=0,
                shots=0,
                carries=0,
                pressures=0,
                interceptions=0,
                ball_recoveries=0,
                dribbles=0,
                duels=0,
                aerial_duels=0,
                dispossessed=0,
                miscontrols=0,
            ),
        ]
    )
    session.commit()

    results = aggregate_season(session, season.id)

    assert len(results) == 1
    assert results[0].matches_played == 1
    assert results[0].minutes_played == 90


def test_aggregate_season_maps_unknown_position_to_none_group(session: Session) -> None:
    season = _make_season(session)
    team = Team(name="Morocco", country="Morocco")
    opponent = Team(name="France", country="France")
    session.add_all([team, opponent])
    session.flush()

    player = Player(name="No Position On Record", primary_position=None)
    session.add(player)
    session.flush()

    match = _make_match(session, season.id, team.id, opponent.id, 1)
    session.add(
        PlayerMatchStat(
            player_id=player.id,
            match_id=match.id,
            team_id=team.id,
            minutes_played=10,
            passes_attempted=1,
            passes_completed=1,
            shots=0,
            carries=0,
            pressures=0,
            interceptions=0,
            ball_recoveries=0,
            dribbles=0,
            duels=0,
            aerial_duels=0,
            dispossessed=0,
            miscontrols=0,
        )
    )
    session.commit()

    results = aggregate_season(session, season.id)

    assert len(results) == 1
    assert results[0].position_group is None
