"""Map a StatsBomb position name onto a coarse position group.

Position groups are used to normalize per-90 stats within a cohort of
similar players (guide section 13: scoring must not treat a striker and a
center-back the same way).
"""

POSITION_GROUP_BY_STATSBOMB_POSITION: dict[str, str] = {
    "Goalkeeper": "GK",
    "Right Back": "FB",
    "Left Back": "FB",
    "Right Wing Back": "FB",
    "Left Wing Back": "FB",
    "Right Center Back": "CB",
    "Center Back": "CB",
    "Left Center Back": "CB",
    "Right Defensive Midfield": "DM",
    "Center Defensive Midfield": "DM",
    "Left Defensive Midfield": "DM",
    "Right Midfield": "CM",
    "Right Center Midfield": "CM",
    "Center Midfield": "CM",
    "Left Center Midfield": "CM",
    "Left Midfield": "CM",
    "Right Attacking Midfield": "AM",
    "Center Attacking Midfield": "AM",
    "Left Attacking Midfield": "AM",
    "Right Wing": "WING",
    "Left Wing": "WING",
    "Right Center Forward": "FW",
    "Center Forward": "FW",
    "Left Center Forward": "FW",
    "Striker": "FW",
    "Secondary Striker": "FW",
}


def map_position_to_group(position: str | None) -> str | None:
    """Return the position group for a StatsBomb position name, or None
    for a missing or unrecognized position."""
    if position is None:
        return None
    return POSITION_GROUP_BY_STATSBOMB_POSITION.get(position)
