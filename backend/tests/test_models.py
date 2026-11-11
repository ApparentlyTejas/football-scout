import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.competition import Competition
from app.models.match import Match
from app.models.player import Player
from app.models.player_external_id import PlayerExternalId
from app.models.player_match_stat import PlayerMatchStat
from app.models.season import Season
from app.models.team import Team


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


def test_unique_constraint_on_player_external_id(session: Session) -> None:
    player_one = Player(name="Lionel Messi")
    player_two = Player(name="Cristiano Ronaldo")
    session.add_all([player_one, player_two])
    session.flush()

    session.add(
        PlayerExternalId(
            player_id=player_one.id, source="statsbomb", external_id="123"
        )
    )
    session.flush()

    session.add(
        PlayerExternalId(
            player_id=player_two.id, source="statsbomb", external_id="123"
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_player_match_stat_round_trip(session: Session) -> None:
    competition = Competition(
        statsbomb_competition_id=11,
        name="La Liga",
        country="Spain",
        gender="male",
    )
    session.add(competition)
    session.flush()

    season = Season(
        competition_id=competition.id,
        statsbomb_season_id=90,
        name="2020/2021",
    )
    session.add(season)
    session.flush()

    home_team = Team(name="Barcelona", country="Spain")
    away_team = Team(name="Real Madrid", country="Spain")
    session.add_all([home_team, away_team])
    session.flush()

    player = Player(
        name="Lionel Messi",
        date_of_birth=datetime.date(1987, 6, 24),
        nationality="Argentina",
        primary_position="Forward",
        market_value=50_000_000.0,
        contract_expiry=datetime.date(2021, 6, 30),
        height=170.0,
    )
    session.add(player)
    session.flush()

    match = Match(
        statsbomb_match_id=303473,
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        match_date=datetime.date(2020, 10, 24),
        home_score=1,
        away_score=3,
    )
    session.add(match)
    session.flush()

    stat = PlayerMatchStat(
        player_id=player.id,
        match_id=match.id,
        team_id=home_team.id,
        minutes_played=90,
        passes_attempted=80,
        passes_completed=65,
        shots=5,
        carries=40,
        pressures=12,
        interceptions=1,
        ball_recoveries=3,
        dribbles=4,
        duels=10,
        aerial_duels=2,
        dispossessed=3,
        miscontrols=2,
    )
    session.add(stat)
    session.commit()

    fetched = (
        session.query(PlayerMatchStat).filter_by(player_id=player.id).one()
    )
    assert fetched.match_id == match.id
    assert fetched.team_id == home_team.id
    assert fetched.minutes_played == 90
    assert fetched.passes_attempted == 80
    assert fetched.passes_completed == 65
    assert fetched.shots == 5
    assert fetched.carries == 40
    assert fetched.pressures == 12
    assert fetched.interceptions == 1
    assert fetched.ball_recoveries == 3
    assert fetched.dribbles == 4
    assert fetched.duels == 10
    assert fetched.aerial_duels == 2
    assert fetched.dispossessed == 3
    assert fetched.miscontrols == 2
