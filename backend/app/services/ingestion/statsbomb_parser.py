"""Pure parsing of StatsBomb open-data JSON into typed dataclasses.

This module has no knowledge of HTTP or the `statsbomb_client` fetch layer:
it only consumes plain dicts shaped like the JSON StatsBomb's open-data API
returns (lineups and events endpoints).
"""

from dataclasses import dataclass


@dataclass
class ParsedPlayerAppearance:
    statsbomb_player_id: int
    name: str
    nationality: str | None
    team_statsbomb_id: int
    team_name: str
    minutes_played: float


@dataclass
class ParsedMatchPlayerStats:
    statsbomb_player_id: int
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


def _parse_clock(value: str) -> float:
    """Parse a StatsBomb "mm:ss" (or "hh:mm:ss") clock string into minutes."""
    parts = [float(p) for p in value.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        minutes += hours * 60
    else:
        raise ValueError(f"Unrecognized clock format: {value!r}")
    return minutes + seconds / 60


def _period_end_minutes(to_period: int | None) -> float:
    """Approximate the clock minute a period ends at, when a position's
    "to" timestamp is missing.

    DOCUMENTED APPROXIMATION: in the verified StatsBomb open-data shape,
    a position with `"to": None` always carries `end_reason == "Final
    Whistle"` -- i.e. the player held that position until the actual end
    of the match, not merely until the end of whichever period it
    started in. So we treat `to_period == 1` as ending at 45 (the one
    case where a position genuinely only spans the first half with no
    further record), and treat everything else (`to_period == 2`, or
    `to_period` missing/None, which is the common "ran to full time"
    case) as ending at 90. This ignores stoppage time beyond 90/45, which
    is an acceptable approximation for this task.
    """
    return 45.0 if to_period == 1 else 90.0


def _position_minutes(position: dict) -> float:
    start = _parse_clock(position["from"])
    to = position.get("to")
    if to is not None:
        end = _parse_clock(to)
    else:
        end = _period_end_minutes(position.get("to_period"))
    return max(0.0, end - start)


def parse_lineups(lineups_json: list[dict]) -> list[ParsedPlayerAppearance]:
    appearances: list[ParsedPlayerAppearance] = []
    for team in lineups_json:
        team_id = team["team_id"]
        team_name = team["team_name"]
        for player in team["lineup"]:
            minutes_played = sum(
                _position_minutes(position) for position in player["positions"]
            )
            country = player.get("country")
            nationality = country["name"] if country else None
            appearances.append(
                ParsedPlayerAppearance(
                    statsbomb_player_id=player["player_id"],
                    name=player["player_name"],
                    nationality=nationality,
                    team_statsbomb_id=team_id,
                    team_name=team_name,
                    minutes_played=minutes_played,
                )
            )
    return appearances


_COUNTER_FIELD_BY_TYPE = {
    "Shot": "shots",
    "Carry": "carries",
    "Pressure": "pressures",
    "Interception": "interceptions",
    "Ball Recovery": "ball_recoveries",
    "Dribble": "dribbles",
    "Dispossessed": "dispossessed",
    "Miscontrol": "miscontrols",
}


def _get_or_create_stats(
    stats_by_player: dict[int, ParsedMatchPlayerStats], player_id: int
) -> ParsedMatchPlayerStats:
    if player_id not in stats_by_player:
        stats_by_player[player_id] = ParsedMatchPlayerStats(statsbomb_player_id=player_id)
    return stats_by_player[player_id]


def parse_events(events_json: list[dict]) -> dict[int, ParsedMatchPlayerStats]:
    stats_by_player: dict[int, ParsedMatchPlayerStats] = {}

    for event in events_json:
        player = event.get("player")
        if not player:
            # Team-level events (e.g. "Half Start") have no player; skip.
            continue

        player_id = player["id"]
        type_name = event["type"]["name"]
        stats = _get_or_create_stats(stats_by_player, player_id)

        if type_name == "Pass":
            stats.passes_attempted += 1
            if "outcome" not in event.get("pass", {}):
                stats.passes_completed += 1
        elif type_name == "Duel":
            stats.duels += 1
            duel_type_name = event.get("duel", {}).get("type", {}).get("name", "")
            if duel_type_name.startswith("Aerial"):
                stats.aerial_duels += 1
        elif type_name in _COUNTER_FIELD_BY_TYPE:
            field_name = _COUNTER_FIELD_BY_TYPE[type_name]
            setattr(stats, field_name, getattr(stats, field_name) + 1)
        # Any other type.name (e.g. "Half Start", "Ball Receipt*") is a
        # no-op: we only track the known counters above.

    return stats_by_player
