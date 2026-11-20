from sqlalchemy.orm import Session

from app.repositories.player_season_stat_repository import upsert_player_season_stat
from app.services.features.percentiles import compute_percentiles
from app.services.features.season_aggregator import aggregate_season


def build_season_features(session: Session, season_id: int) -> int:
    """Aggregate and rank one season's PlayerMatchStat rows, upserting a
    PlayerSeasonStat row per player. Returns the number of players
    processed."""
    aggregates = aggregate_season(session, season_id)
    percentiles_by_player = compute_percentiles(aggregates)

    for aggregate in aggregates:
        upsert_player_season_stat(
            session,
            aggregate,
            percentiles_by_player[aggregate.player_id],
            season_id,
        )

    return len(aggregates)
