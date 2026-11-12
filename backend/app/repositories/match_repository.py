import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match


def get_or_create_match(
    session: Session,
    statsbomb_match_id: int,
    season_id: int,
    home_team_id: int,
    away_team_id: int,
    match_date: datetime.date,
    home_score: int,
    away_score: int,
) -> Match:
    """Look up a Match by its StatsBomb id, updating it in place to match
    the given fields if found, or creating it if missing."""
    match = session.execute(
        select(Match).where(Match.statsbomb_match_id == statsbomb_match_id)
    ).scalar_one_or_none()

    if match is None:
        match = Match(
            statsbomb_match_id=statsbomb_match_id,
            season_id=season_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            match_date=match_date,
            home_score=home_score,
            away_score=away_score,
        )
        session.add(match)
    else:
        match.season_id = season_id
        match.home_team_id = home_team_id
        match.away_team_id = away_team_id
        match.match_date = match_date
        match.home_score = home_score
        match.away_score = away_score

    session.flush()
    return match
