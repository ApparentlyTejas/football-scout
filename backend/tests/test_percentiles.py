from app.services.features.percentiles import (
    MIN_MINUTES_FOR_PERCENTILE,
    compute_percentile_rank,
    compute_percentiles,
)
from app.services.features.season_aggregator import PlayerSeasonAggregate


def _aggregate(player_id: int, position_group: str | None, minutes_played: int, shots_per_90: float | None) -> PlayerSeasonAggregate:
    return PlayerSeasonAggregate(
        player_id=player_id,
        team_id=1,
        position_group=position_group,
        matches_played=1,
        minutes_played=minutes_played,
        shots_per_90=shots_per_90,
    )


def test_compute_percentile_rank_formula() -> None:
    cohort_values = [1.0, 2.0, 3.0, 4.0]
    assert compute_percentile_rank(1.0, cohort_values) == 12.5
    assert compute_percentile_rank(4.0, cohort_values) == 87.5
    assert compute_percentile_rank(2.5, cohort_values) == 50.0


def test_compute_percentile_rank_single_value_cohort() -> None:
    assert compute_percentile_rank(5.0, [5.0]) == 50.0


def test_compute_percentiles_groups_by_season_and_position_group() -> None:
    fw_low = _aggregate(1, "FW", MIN_MINUTES_FOR_PERCENTILE, 1.0)
    fw_high = _aggregate(2, "FW", MIN_MINUTES_FOR_PERCENTILE, 3.0)
    cm_lone = _aggregate(3, "CM", MIN_MINUTES_FOR_PERCENTILE, 2.0)

    results = compute_percentiles([fw_low, fw_high, cm_lone])

    assert results[1].shots_per_90_percentile == 25.0
    assert results[2].shots_per_90_percentile == 75.0
    assert results[3].shots_per_90_percentile == 50.0


def test_compute_percentiles_excludes_players_below_minute_threshold() -> None:
    below_threshold = _aggregate(1, "FW", 100, 10.0)
    qualifying_one = _aggregate(2, "FW", MIN_MINUTES_FOR_PERCENTILE, 2.0)
    qualifying_two = _aggregate(3, "FW", MIN_MINUTES_FOR_PERCENTILE, 2.0)

    results = compute_percentiles([below_threshold, qualifying_one, qualifying_two])

    assert results[1].shots_per_90_percentile is None
    assert results[2].shots_per_90_percentile == 50.0
    assert results[3].shots_per_90_percentile == 50.0


def test_compute_percentiles_handles_none_per_90_value() -> None:
    missing_value = _aggregate(1, "FW", MIN_MINUTES_FOR_PERCENTILE, None)
    qualifying = _aggregate(2, "FW", MIN_MINUTES_FOR_PERCENTILE, 2.0)

    results = compute_percentiles([missing_value, qualifying])

    assert results[1].shots_per_90_percentile is None
    assert results[2].shots_per_90_percentile == 50.0
