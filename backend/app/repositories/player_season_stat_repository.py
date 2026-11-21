from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.player_season_stat import PlayerSeasonStat
from app.services.features.percentiles import PER_90_FIELDS, PlayerSeasonPercentiles
from app.services.features.season_aggregator import RAW_COUNTER_FIELDS, PlayerSeasonAggregate

_PASS_THROUGH_FIELDS = ("team_id", "position_group", "matches_played", "minutes_played")


def upsert_player_season_stat(
    session: Session,
    aggregate: PlayerSeasonAggregate,
    percentiles: PlayerSeasonPercentiles,
    season_id: int,
) -> PlayerSeasonStat:
    """Create or update-in-place the `(player_id, season_id)` row for one
    player's season aggregate and percentiles."""
    row = session.execute(
        select(PlayerSeasonStat).where(
            PlayerSeasonStat.player_id == aggregate.player_id,
            PlayerSeasonStat.season_id == season_id,
        )
    ).scalar_one_or_none()

    if row is None:
        row = PlayerSeasonStat(player_id=aggregate.player_id, season_id=season_id)
        session.add(row)

    for field in _PASS_THROUGH_FIELDS:
        setattr(row, field, getattr(aggregate, field))
    for field in RAW_COUNTER_FIELDS:
        setattr(row, field, getattr(aggregate, field))
    for field in PER_90_FIELDS:
        setattr(row, field, getattr(aggregate, field))
        setattr(row, f"{field}_percentile", getattr(percentiles, f"{field}_percentile"))

    session.flush()
    return row
