from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competition import Competition


def get_or_create_competition(
    session: Session,
    statsbomb_competition_id: int,
    name: str,
    country: str,
    gender: str,
) -> Competition:
    """Look up a Competition by its StatsBomb id, updating it in place to
    match the given fields if found, or creating it if missing."""
    competition = session.execute(
        select(Competition).where(
            Competition.statsbomb_competition_id == statsbomb_competition_id
        )
    ).scalar_one_or_none()

    if competition is None:
        competition = Competition(
            statsbomb_competition_id=statsbomb_competition_id,
            name=name,
            country=country,
            gender=gender,
        )
        session.add(competition)
    else:
        competition.name = name
        competition.country = country
        competition.gender = gender

    session.flush()
    return competition
