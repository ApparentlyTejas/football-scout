"""Pure aggregation of a season's PlayerMatchStat rows into per-90 rates.

No HTTP, no upserts: this module only reads PlayerMatchStat/Match/Player
rows for one season and sums them in Python.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.player import Player
from app.models.player_match_stat import PlayerMatchStat
from app.services.features.position_groups import map_position_to_group

RAW_COUNTER_FIELDS = (
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


@dataclass
class PlayerSeasonAggregate:
    player_id: int
    team_id: int
    position_group: str | None
    matches_played: int
    minutes_played: int
    passes_attempted: int = 0
    passes_completed: int = 0
    shots: int = 0
    carries: int = 0
    pressures: int = 0
    interceptions: int = 0
    ball_recoveries: int = 0
    dribbles: int = 0
    duels: int = 0
    aerial_duels: int = 0
    dispossessed: int = 0
    miscontrols: int = 0
    pass_completion_pct: float | None = None
    passes_per_90: float | None = None
    shots_per_90: float | None = None
    carries_per_90: float | None = None
    pressures_per_90: float | None = None
    interceptions_per_90: float | None = None
    ball_recoveries_per_90: float | None = None
    dribbles_per_90: float | None = None
    duels_per_90: float | None = None
    aerial_duels_per_90: float | None = None
    dispossessed_per_90: float | None = None
    miscontrols_per_90: float | None = None


def _per_90(total: int, minutes_played: int) -> float | None:
    return total * 90 / minutes_played if minutes_played > 0 else None


def aggregate_season(session: Session, season_id: int) -> list[PlayerSeasonAggregate]:
    """Sum every player's PlayerMatchStat rows for one season into a
    PlayerSeasonAggregate per player."""
    rows = session.execute(
        select(PlayerMatchStat, Match)
        .join(Match, PlayerMatchStat.match_id == Match.id)
        .where(Match.season_id == season_id)
    ).all()

    by_player: dict[int, list[tuple[PlayerMatchStat, Match]]] = {}
    for stat, match in rows:
        by_player.setdefault(stat.player_id, []).append((stat, match))

    aggregates: list[PlayerSeasonAggregate] = []
    for player_id, stat_match_pairs in by_player.items():
        totals = {field: 0 for field in RAW_COUNTER_FIELDS}
        minutes_played = 0
        for stat, _match in stat_match_pairs:
            minutes_played += stat.minutes_played
            for field in RAW_COUNTER_FIELDS:
                totals[field] += getattr(stat, field)

        latest_stat, _latest_match = max(
            stat_match_pairs, key=lambda pair: pair[1].match_date
        )

        player = session.get(Player, player_id)
        position_group = map_position_to_group(
            player.primary_position if player is not None else None
        )

        aggregates.append(
            PlayerSeasonAggregate(
                player_id=player_id,
                team_id=latest_stat.team_id,
                position_group=position_group,
                matches_played=len(stat_match_pairs),
                minutes_played=minutes_played,
                pass_completion_pct=(
                    totals["passes_completed"] / totals["passes_attempted"] * 100
                    if totals["passes_attempted"] > 0
                    else None
                ),
                passes_per_90=_per_90(totals["passes_attempted"], minutes_played),
                shots_per_90=_per_90(totals["shots"], minutes_played),
                carries_per_90=_per_90(totals["carries"], minutes_played),
                pressures_per_90=_per_90(totals["pressures"], minutes_played),
                interceptions_per_90=_per_90(totals["interceptions"], minutes_played),
                ball_recoveries_per_90=_per_90(
                    totals["ball_recoveries"], minutes_played
                ),
                dribbles_per_90=_per_90(totals["dribbles"], minutes_played),
                duels_per_90=_per_90(totals["duels"], minutes_played),
                aerial_duels_per_90=_per_90(totals["aerial_duels"], minutes_played),
                dispossessed_per_90=_per_90(totals["dispossessed"], minutes_played),
                miscontrols_per_90=_per_90(totals["miscontrols"], minutes_played),
                **totals,
            )
        )

    return aggregates
