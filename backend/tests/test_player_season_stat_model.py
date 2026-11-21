import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.competition import Competition
from app.models.player import Player
from app.models.player_season_stat import PlayerSeasonStat
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


def _seed_ids(session: Session) -> tuple[int, int, int]:
    competition = Competition(
        statsbomb_competition_id=43, name="FIFA World Cup", country="International", gender="male"
    )
    session.add(competition)
    session.flush()
    season = Season(competition_id=competition.id, statsbomb_season_id=106, name="2022")
    player = Player(name="Lionel Messi")
    team = Team(name="Argentina", country="Argentina")
    session.add_all([season, player, team])
    session.flush()
    return player.id, season.id, team.id


def test_unique_constraint_on_player_season(session: Session) -> None:
    player_id, season_id, team_id = _seed_ids(session)

    session.add(
        PlayerSeasonStat(
            player_id=player_id,
            season_id=season_id,
            team_id=team_id,
            matches_played=1,
            minutes_played=90,
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
    session.flush()

    session.add(
        PlayerSeasonStat(
            player_id=player_id,
            season_id=season_id,
            team_id=team_id,
            matches_played=1,
            minutes_played=90,
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
    with pytest.raises(IntegrityError):
        session.flush()


def test_player_season_stat_round_trip(session: Session) -> None:
    player_id, season_id, team_id = _seed_ids(session)

    stat = PlayerSeasonStat(
        player_id=player_id,
        season_id=season_id,
        team_id=team_id,
        position_group="FW",
        matches_played=7,
        minutes_played=630,
        passes_attempted=140,
        passes_completed=119,
        shots=21,
        carries=98,
        pressures=63,
        interceptions=7,
        ball_recoveries=14,
        dribbles=28,
        duels=42,
        aerial_duels=21,
        dispossessed=14,
        miscontrols=7,
        pass_completion_pct=85.0,
        passes_per_90=20.0,
        shots_per_90=3.0,
        carries_per_90=14.0,
        pressures_per_90=9.0,
        interceptions_per_90=1.0,
        ball_recoveries_per_90=2.0,
        dribbles_per_90=4.0,
        duels_per_90=6.0,
        aerial_duels_per_90=3.0,
        dispossessed_per_90=2.0,
        miscontrols_per_90=1.0,
        pass_completion_pct_percentile=60.0,
        passes_per_90_percentile=55.0,
        shots_per_90_percentile=92.0,
        carries_per_90_percentile=None,
        pressures_per_90_percentile=None,
        interceptions_per_90_percentile=10.0,
        ball_recoveries_per_90_percentile=20.0,
        dribbles_per_90_percentile=30.0,
        duels_per_90_percentile=40.0,
        aerial_duels_per_90_percentile=50.0,
        dispossessed_per_90_percentile=60.0,
        miscontrols_per_90_percentile=70.0,
    )
    session.add(stat)
    session.commit()

    fetched = session.query(PlayerSeasonStat).filter_by(player_id=player_id).one()
    assert fetched.season_id == season_id
    assert fetched.team_id == team_id
    assert fetched.position_group == "FW"
    assert fetched.matches_played == 7
    assert fetched.minutes_played == 630
    assert fetched.passes_attempted == 140
    assert fetched.passes_completed == 119
    assert fetched.shots == 21
    assert fetched.carries == 98
    assert fetched.pressures == 63
    assert fetched.interceptions == 7
    assert fetched.ball_recoveries == 14
    assert fetched.dribbles == 28
    assert fetched.duels == 42
    assert fetched.aerial_duels == 21
    assert fetched.dispossessed == 14
    assert fetched.miscontrols == 7
    assert fetched.pass_completion_pct == 85.0
    assert fetched.passes_per_90 == 20.0
    assert fetched.shots_per_90 == 3.0
    assert fetched.carries_per_90 == 14.0
    assert fetched.pressures_per_90 == 9.0
    assert fetched.interceptions_per_90 == 1.0
    assert fetched.ball_recoveries_per_90 == 2.0
    assert fetched.dribbles_per_90 == 4.0
    assert fetched.duels_per_90 == 6.0
    assert fetched.aerial_duels_per_90 == 3.0
    assert fetched.dispossessed_per_90 == 2.0
    assert fetched.miscontrols_per_90 == 1.0
    assert fetched.pass_completion_pct_percentile == 60.0
    assert fetched.passes_per_90_percentile == 55.0
    assert fetched.shots_per_90_percentile == 92.0
    assert fetched.carries_per_90_percentile is None
    assert fetched.pressures_per_90_percentile is None
    assert fetched.interceptions_per_90_percentile == 10.0
    assert fetched.ball_recoveries_per_90_percentile == 20.0
    assert fetched.dribbles_per_90_percentile == 30.0
    assert fetched.duels_per_90_percentile == 40.0
    assert fetched.aerial_duels_per_90_percentile == 50.0
    assert fetched.dispossessed_per_90_percentile == 60.0
    assert fetched.miscontrols_per_90_percentile == 70.0
