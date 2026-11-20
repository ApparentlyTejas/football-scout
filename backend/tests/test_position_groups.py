from app.services.features.position_groups import map_position_to_group

CANONICAL_STATSBOMB_POSITIONS = [
    "Goalkeeper",
    "Right Back",
    "Right Center Back",
    "Center Back",
    "Left Center Back",
    "Left Back",
    "Right Wing Back",
    "Left Wing Back",
    "Right Defensive Midfield",
    "Center Defensive Midfield",
    "Left Defensive Midfield",
    "Right Midfield",
    "Right Center Midfield",
    "Center Midfield",
    "Left Center Midfield",
    "Left Midfield",
    "Right Wing",
    "Right Attacking Midfield",
    "Center Attacking Midfield",
    "Left Attacking Midfield",
    "Left Wing",
    "Right Center Forward",
    "Center Forward",
    "Left Center Forward",
    "Striker",
    "Secondary Striker",
]

KNOWN_GROUPS = {"GK", "CB", "FB", "DM", "CM", "AM", "WING", "FW"}


def test_map_position_to_group_covers_all_canonical_statsbomb_positions() -> None:
    for position in CANONICAL_STATSBOMB_POSITIONS:
        group = map_position_to_group(position)
        assert group in KNOWN_GROUPS, f"{position!r} mapped to {group!r}"


def test_map_position_to_group_handles_unknown_and_none() -> None:
    assert map_position_to_group(None) is None
    assert map_position_to_group("Not A Real Position") is None
