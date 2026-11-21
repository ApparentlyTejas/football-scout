import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.competition import Competition
from app.models.match import Match
from app.models.player import Player
from app.models.player_match_stat import PlayerMatchStat
from app.models.player_season_stat import PlayerSeasonStat
from app.models.season import Season
from app.models.team import Team
from app.services.features.player_season_stats_builder import build_season_features


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


def _seed_two_match_player(session: Session) -> int:
    competition = Competition(
        statsbomb_competition_id=43, name="FIFA World Cup", country="International", gender="male"
    )
    session.add(competition)
    session.flush()
    season = Season(competition_id=competition.id, statsbomb_season_id=106, name="2022")
    session.add(season)
    session.flush()

    team = Team(name="Morocco", country="Morocco")
    opponent = Team(name="France", country="France")
    session.add_all([team, opponent])
    session.flush()

    player = Player(name="Youssef En-Nesyri", primary_position="Center Forward")
    session.add(player)
    session.flush()

    match1 = Match(
        statsbomb_match_id=1,
        season_id=season.id,
        home_team_id=team.id,
        away_team_id=opponent.id,
        match_date=datetime.date(2022, 11, 21),
        home_score=1,
        away_score=0,
    )
    match2 = Match(
        statsbomb_match_id=2,
        season_id=season.id,
        home_team_id=team.id,
        away_team_id=opponent.id,
        match_date=datetime.date(2022, 11, 22),
        home_score=1,
        away_score=0,
    )
    session.add_all([match1, match2])
    session.flush()

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
    return season.id


def test_build_season_features_creates_expected_rows(session: Session) -> None:
    season_id = _seed_two_match_player(session)

    count = build_season_features(session, season_id)

    assert count == 1
    rows = list(session.execute(select(PlayerSeasonStat)).scalars())
    assert len(rows) == 1
    assert rows[0].shots_per_90 == 3.0
    assert rows[0].position_group == "FW"
    # 90 season minutes is below MIN_MINUTES_FOR_PERCENTILE (270), so this
    # player is excluded from percentile ranking per Task 2's minutes
    # reliability rule.
    assert rows[0].shots_per_90_percentile is None


def test_build_season_features_is_idempotent(session: Session) -> None:
    season_id = _seed_two_match_player(session)

    build_season_features(session, season_id)
    build_season_features(session, season_id)

    rows = list(session.execute(select(PlayerSeasonStat)).scalars())
    assert len(rows) == 1
    assert rows[0].shots_per_90 == 3.0
