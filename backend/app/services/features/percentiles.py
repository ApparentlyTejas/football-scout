"""Within-cohort percentile ranking for a season's player aggregates.

Methodology (spec section 14, "percentile within competition"): a
player's percentile for a metric is their rank among same-position-group
teammates with reliable minutes, using the formula

    (count_strictly_below + 0.5 * count_equal) / n * 100

(a tie splits the difference rather than favoring either side; a lone
cohort member ranks at the middle, 50.0, rather than dividing by zero).
Minutes reliability (spec section 12) is enforced by excluding any player
with fewer than MIN_MINUTES_FOR_PERCENTILE season minutes from both being
ranked and from the cohort other players are ranked against.
"""

from dataclasses import dataclass, fields

from app.services.features.season_aggregator import PlayerSeasonAggregate

MIN_MINUTES_FOR_PERCENTILE = 270

PER_90_FIELDS: tuple[str, ...] = (
    "pass_completion_pct",
    "passes_per_90",
    "shots_per_90",
    "carries_per_90",
    "pressures_per_90",
    "interceptions_per_90",
    "ball_recoveries_per_90",
    "dribbles_per_90",
    "duels_per_90",
    "aerial_duels_per_90",
    "dispossessed_per_90",
    "miscontrols_per_90",
)


@dataclass
class PlayerSeasonPercentiles:
    player_id: int
    pass_completion_pct_percentile: float | None = None
    passes_per_90_percentile: float | None = None
    shots_per_90_percentile: float | None = None
    carries_per_90_percentile: float | None = None
    pressures_per_90_percentile: float | None = None
    interceptions_per_90_percentile: float | None = None
    ball_recoveries_per_90_percentile: float | None = None
    dribbles_per_90_percentile: float | None = None
    duels_per_90_percentile: float | None = None
    aerial_duels_per_90_percentile: float | None = None
    dispossessed_per_90_percentile: float | None = None
    miscontrols_per_90_percentile: float | None = None


assert {f"{name}_percentile" for name in PER_90_FIELDS} == {
    f.name for f in fields(PlayerSeasonPercentiles) if f.name != "player_id"
}


def compute_percentile_rank(value: float, cohort_values: list[float]) -> float:
    """Rank `value` within `cohort_values` as a percentile (0-100)."""
    below = sum(1 for v in cohort_values if v < value)
    equal = sum(1 for v in cohort_values if v == value)
    return (below + 0.5 * equal) / len(cohort_values) * 100


def compute_percentiles(
    aggregates: list[PlayerSeasonAggregate],
) -> dict[int, PlayerSeasonPercentiles]:
    """Rank every aggregate's per-90 fields within its position-group
    cohort, restricted to players with reliable minutes."""
    qualifying = [a for a in aggregates if a.minutes_played >= MIN_MINUTES_FOR_PERCENTILE]

    results = {a.player_id: PlayerSeasonPercentiles(player_id=a.player_id) for a in aggregates}

    cohorts: dict[str | None, list[PlayerSeasonAggregate]] = {}
    for aggregate in qualifying:
        cohorts.setdefault(aggregate.position_group, []).append(aggregate)

    for field_name in PER_90_FIELDS:
        for cohort in cohorts.values():
            cohort_values = [
                getattr(a, field_name)
                for a in cohort
                if getattr(a, field_name) is not None
            ]
            for aggregate in cohort:
                value = getattr(aggregate, field_name)
                if value is None:
                    continue
                percentile = compute_percentile_rank(value, cohort_values)
                setattr(results[aggregate.player_id], f"{field_name}_percentile", percentile)

    return results
