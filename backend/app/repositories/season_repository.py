from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.season import Season


def get_or_create_season(
    session: Session,
    competition_id: int,
    statsbomb_season_id: int,
    name: str,
) -> Season:
    """Look up a Season by (competition_id, statsbomb_season_id), updating
    it in place to match the given fields if found, or creating it if
    missing."""
    season = session.execute(
        select(Season).where(
            Season.competition_id == competition_id,
            Season.statsbomb_season_id == statsbomb_season_id,
        )
    ).scalar_one_or_none()

    if season is None:
        season = Season(
            competition_id=competition_id,
            statsbomb_season_id=statsbomb_season_id,
            name=name,
        )
        session.add(season)
    else:
        season.name = name

    session.flush()
    return season
