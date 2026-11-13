from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.player_match_stat import PlayerMatchStat
from app.services.ingestion.statsbomb_parser import ParsedMatchPlayerStats

_COUNTER_FIELDS = (
    "passes_attempted",
    "passes_completed",
    "shots",
    "carries",
    "pressures",
    "interceptions",
    "ball_recoveries",
    "dribbles",
    "duels",
    "aerial_duels",
    "dispossessed",
    "miscontrols",
)


def upsert_player_match_stat(
    session: Session,
    player_id: int,
    match_id: int,
    team_id: int,
    stats: ParsedMatchPlayerStats | None,
    minutes_played: float,
) -> PlayerMatchStat:
    """Create or update-in-place the `(player_id, match_id)` stats row for
    one player's appearance. `stats` is `None` for a player who had no
    events recorded at all, in which case every counter is stored as 0."""
    # `PlayerMatchStat.minutes_played` is an Integer column, while the
    # parser's minutes are a float (fractional minutes from mm:ss clocks).
    # Round to the nearest whole minute to match the column's type.
    minutes_played_int = round(minutes_played)

    row = session.execute(
        select(PlayerMatchStat).where(
            PlayerMatchStat.player_id == player_id,
            PlayerMatchStat.match_id == match_id,
        )
    ).scalar_one_or_none()

    counter_values = {
        field: getattr(stats, field) if stats is not None else 0
        for field in _COUNTER_FIELDS
    }

    if row is None:
        row = PlayerMatchStat(
            player_id=player_id,
            match_id=match_id,
            team_id=team_id,
            minutes_played=minutes_played_int,
            **counter_values,
        )
        session.add(row)
    else:
        row.team_id = team_id
        row.minutes_played = minutes_played_int
        for field, value in counter_values.items():
            setattr(row, field, value)

    session.flush()
    return row
