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
    # The StatsBomb position name (e.g. "Center Forward") the player spent
    # the most minutes in this match; None if they have no position records
    # (an unused substitute).
    position: str | None = None


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
    """Fallback match-end approximation, used only when `parse_lineups`
    is not given the match's events.

    A position with `"to": None` carries `end_reason == "Final Whistle"`,
    so the player held it until the end of the match. Without events we
    can't know when that was, so `to_period == 1` is treated as ending at
    45 and everything else as ending at 90, ignoring stoppage and extra
    time. Pass `events_json` to `parse_lineups` for the real match end.
    """
    return 45.0 if to_period == 1 else 90.0


# Period 5 is the penalty shootout: its events carry clock minutes
# (120:00 onwards) but it is not playing time.
_PENALTY_SHOOTOUT_PERIOD = 5


def _match_end_minutes(events_json: list[dict] | None) -> float | None:
    """The match clock (in minutes) at the last moment of play: the latest
    `minute`/`second` over all events outside the penalty shootout, which
    in real data is the final "Half End" event (e.g. 93:54 for a regular
    match, 124:07 for the 2022 World Cup final). None if there are no
    events to look at."""
    clocks = [
        event["minute"] + event["second"] / 60
        for event in events_json or []
        if event.get("period", 0) < _PENALTY_SHOOTOUT_PERIOD
    ]
    return max(clocks) if clocks else None


def _is_permanent_exit(end_reason: str) -> bool:
    """A position ending in a substitution off or a red card means the
    player left the match for good (unlike "Player Off", a temporary
    exit such as for treatment)."""
    return end_reason.startswith("Substitution - Off") or "Red Card" in end_reason


def _position_interval(
    position: dict, match_end: float | None
) -> tuple[float, float] | None:
    """The (start, end) match-clock minutes of one position record, or
    None if the record is empty or runs backwards.

    Real StatsBomb lineups occasionally contain records whose "to" is
    earlier than their "from" (e.g. Messi's "115:32" -> "28:11" in the
    2022 final): the times belong to neighbouring records, which cover
    that span anyway, so such a record is skipped rather than counted.
    """
    start = _parse_clock(position["from"])
    to = position.get("to")
    if to is not None:
        end = _parse_clock(to)
    elif match_end is not None:
        end = match_end
    else:
        end = _period_end_minutes(position.get("to_period"))
    if end <= start:
        return None
    return start, end


def _minutes_played(positions: list[dict], match_end: float | None) -> float:
    """Total minutes a player was on the pitch.

    Position records can overlap (real data has e.g. a 00:00-120:35
    record alongside an open-ended 41:20 one after a formation change),
    so the intervals are merged before summing rather than added up
    record by record. The result is then clipped at the player's earliest
    permanent exit (substitution off / red card): in real data an
    overlapping open-ended record can otherwise outlive the substitution.
    """
    intervals = []
    exit_at = None
    for position in positions:
        interval = _position_interval(position, match_end)
        if interval is None:
            continue
        intervals.append(interval)
        if position.get("to") is not None and _is_permanent_exit(
            position.get("end_reason", "")
        ):
            exit_at = interval[1] if exit_at is None else min(exit_at, interval[1])

    total = 0.0
    current_start = current_end = None
    for start, end in sorted(intervals):
        if exit_at is not None:
            end = min(end, exit_at)
            if end <= start:
                continue
        if current_end is None or start > current_end:
            if current_end is not None:
                total += current_end - current_start
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    if current_end is not None:
        total += current_end - current_start
    return total


def _main_position(positions: list[dict], match_end: float | None) -> str | None:
    """The position name with the most total minutes across the player's
    records (ties go to the one listed first), or None if no record
    covers any time."""
    minutes_by_position: dict[str, float] = {}
    for position in positions:
        interval = _position_interval(position, match_end)
        if interval is None:
            continue
        name = position["position"]
        minutes_by_position[name] = (
            minutes_by_position.get(name, 0.0) + interval[1] - interval[0]
        )
    if not minutes_by_position:
        return None
    return max(minutes_by_position, key=minutes_by_position.__getitem__)


def parse_lineups(
    lineups_json: list[dict], events_json: list[dict] | None = None
) -> list[ParsedPlayerAppearance]:
    """Parse each lineup player into an appearance.

    `events_json` (the same match's events) is used to find the real
    match end for open-ended positions; without it (or if it is empty),
    open-ended positions fall back to ending at 45 or 90.
    """
    match_end = _match_end_minutes(events_json)
    appearances: list[ParsedPlayerAppearance] = []
    for team in lineups_json:
        team_id = team["team_id"]
        team_name = team["team_name"]
        for player in team["lineup"]:
            minutes_played = _minutes_played(player["positions"], match_end)
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
                    position=_main_position(player["positions"], match_end),
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


# In real StatsBomb data, a Duel's `duel.type.name` is only ever "Aerial
# Lost" or "Tackle": there is no "Aerial Won" duel type. An aerial win is
# instead an `aerial_won: true` flag inside the event's own sub-object,
# verified on real events for these four types (e.g. `event["pass"]
# ["aerial_won"]`).
_AERIAL_WON_KEY_BY_TYPE = {
    "Pass": "pass",
    "Clearance": "clearance",
    "Shot": "shot",
    "Miscontrol": "miscontrol",
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
            if duel_type_name == "Aerial Lost":
                stats.aerial_duels += 1
        elif type_name in _COUNTER_FIELD_BY_TYPE:
            field_name = _COUNTER_FIELD_BY_TYPE[type_name]
            setattr(stats, field_name, getattr(stats, field_name) + 1)
        # Any other type.name (e.g. "Half Start", "Ball Receipt*") is a
        # no-op: we only track the known counters above.

        # `aerial_duels` is the total contested (won + lost): the losses
        # are counted from Duel events above, the wins here.
        aerial_won_key = _AERIAL_WON_KEY_BY_TYPE.get(type_name)
        if aerial_won_key and event.get(aerial_won_key, {}).get("aerial_won"):
            stats.aerial_duels += 1

    return stats_by_player
