from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team


def get_or_create_team(
    session: Session,
    name: str,
    country: str | None,
) -> Team:
    """Look up a Team by name, updating its country in place to match the
    given value if found, or creating it if missing.

    `Team` has no StatsBomb id column of its own, so name is the natural
    key here; this is adequate for the StatsBomb open-data set where team
    names are stable and unambiguous.

    `Team.country` is a NOT NULL column, but StatsBomb's lineups payload
    does not carry a team country. Callers that don't have one pass
    `None`, which we store as `""` (empty string) rather than leaving the
    column null.
    """
    resolved_country = country if country is not None else ""

    team = session.execute(
        select(Team).where(Team.name == name)
    ).scalar_one_or_none()

    if team is None:
        team = Team(name=name, country=resolved_country)
        session.add(team)
    else:
        team.country = resolved_country

    session.flush()
    return team
