import json
from pathlib import Path

from app.services.ingestion.statsbomb_parser import parse_events, parse_lineups

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "statsbomb"


def _load_fixture(name: str) -> list[dict]:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


def test_parse_lineups_returns_all_players_with_minutes() -> None:
    lineups_json = _load_fixture("lineups_3857276.json")

    appearances = parse_lineups(lineups_json)

    total_players = sum(len(team["lineup"]) for team in lineups_json)
    assert len(appearances) == total_players

    by_id = {a.statsbomb_player_id: a for a in appearances}

    # Youssef En-Nesyri (6301) started and, despite a tactical position
    # change at 76:14, has an open-ended second position with no
    # "to_period" set, which our approximation resolves to the end of the
    # match -> ~90 minutes.
    en_nesyri = by_id[6301]
    assert en_nesyri.name == "Youssef En-Nesyri"
    assert en_nesyri.team_statsbomb_id == 788
    assert en_nesyri.team_name == "Morocco"
    assert abs(en_nesyri.minutes_played - 90) <= 1

    # Zakaria Aboukhlal (21736) entered as a substitute at 64:10 and his
    # final position also has no "to", so it's capped at 90 too, giving a
    # much smaller total than a full-match player.
    aboukhlal = by_id[21736]
    assert aboukhlal.minutes_played < 30
    assert aboukhlal.minutes_played > 20


# events_3857276.json is a trimmed subset of the REAL StatsBomb open-data
# events file for match 3857276 (Morocco vs Canada), events copied
# unmodified. It contains:
# - every real event for Youssef En-Nesyri (6301), except that only 2 of
#   his 30 "Ball Receipt*" events are kept (they are not counted, so his
#   counters below equal his true full-match values);
# - Sofiane Boufal's (3625) Duel, Dispossessed and Interception events
#   plus his one aerial-won Pass (a partial profile);
# - the team-level "Half Start"/"Half End" events (no "player" key).
EN_NESYRI_EXPECTED = {
    "passes_attempted": 18,
    "passes_completed": 12,
    "shots": 2,
    "carries": 21,
    "pressures": 16,
    "interceptions": 0,
    "ball_recoveries": 4,
    "dribbles": 4,
    "duels": 4,
    # 3 "Aerial Lost" Duel events (minutes 0, 66, 71) + 3 aerial wins
    # flagged on a Pass (25', 26') and a Clearance (74').
    "aerial_duels": 6,
    "dispossessed": 0,
    "miscontrols": 3,
}


def _assert_en_nesyri(stats) -> None:
    actual = {field: getattr(stats, field) for field in EN_NESYRI_EXPECTED}
    assert actual == EN_NESYRI_EXPECTED


def test_parse_events_counts_known_player_correctly() -> None:
    events_json = _load_fixture("events_3857276.json")

    stats = parse_events(events_json)

    _assert_en_nesyri(stats[6301])

    boufal_stats = stats[3625]
    assert boufal_stats.duels == 5
    assert boufal_stats.interceptions == 1
    assert boufal_stats.dispossessed == 1
    assert boufal_stats.passes_attempted == 1
    assert boufal_stats.passes_completed == 0


def test_parse_events_counts_aerial_wins_and_losses() -> None:
    events_json = _load_fixture("events_3857276.json")

    stats = parse_events(events_json)

    # Real StatsBomb data has no "Aerial Won" Duel type: an aerial win is
    # an `aerial_won: true` flag on a Pass/Clearance/Shot/Miscontrol.
    # Boufal: 2 "Aerial Lost" Duels + 1 aerial-won Pass (minute 49).
    assert stats[3625].aerial_duels == 3


def test_parse_events_ignores_unknown_event_types() -> None:
    events_json = _load_fixture("events_3857276.json")

    # The fixture includes unrecognized events of two kinds:
    # - "Half Start"/"Half End": team-level, no "player" key at all.
    # - "Ball Receipt*", "Block", "Foul Won", "Foul Committed": have a
    #   real player (6301) but are not in the known-counter mapping.
    # All must be skipped without raising or affecting counted stats.
    stats = parse_events(events_json)

    assert set(stats.keys()) == {6301, 3625}
    _assert_en_nesyri(stats[6301])


# World Cup 2022 final (3869685), real StatsBomb data: went to extra time
# and penalties. lineups_3869685.json is the full real lineups file;
# events_3869685_period_markers.json keeps only the real "Half Start" /
# "Half End" events, which is all parse_lineups needs to find the match
# end. Period 4 (extra time, second half) ends at 124:07; period 5 is the
# penalty shootout (clock 120:00-125:58) and is not playing time.
FINAL_MATCH_END = 124 + 7 / 60


def _final_appearances() -> dict[int, object]:
    appearances = parse_lineups(
        _load_fixture("lineups_3869685.json"),
        _load_fixture("events_3869685_period_markers.json"),
    )
    return {a.statsbomb_player_id: a for a in appearances}


def test_parse_lineups_credits_extra_time_substitutes() -> None:
    by_id = _final_appearances()

    # Axel Disasi came on at 120:35 (period 4), open-ended to full time.
    assert abs(by_id[7439].minutes_played - (FINAL_MATCH_END - (120 + 35 / 60))) < 0.01
    # Youssouf Fofana came on at 95:10 (period 3).
    assert abs(by_id[11990].minutes_played - (FINAL_MATCH_END - (95 + 10 / 60))) < 0.01
    # Hugo Lloris played the whole 120' + stoppage, no longer capped at 90.
    assert abs(by_id[3099].minutes_played - FINAL_MATCH_END) < 0.01


def test_parse_lineups_merges_overlapping_position_records() -> None:
    by_id = _final_appearances()

    for appearance in by_id.values():
        assert 0 <= appearance.minutes_played <= 125

    # Lionel Messi: records 00:00-115:32, 115:32-28:11 (a real record whose
    # "to" is earlier than its "from") and 28:19-open. Naively summed this
    # was ~177 minutes; merged, he covers the whole match.
    assert abs(by_id[5503].minutes_played - FINAL_MATCH_END) < 0.01

    # Jules Kounde: 00:00-120:35 ending "Substitution - Off (Tactical)",
    # plus an overlapping open-ended 41:20 record. Naively ~169 minutes;
    # he really left at 120:35.
    assert abs(by_id[4445].minutes_played - (120 + 35 / 60)) < 0.01
    # Raphael Varane: same shape, off injured at 112:28 (naively ~161).
    assert abs(by_id[5485].minutes_played - (112 + 28 / 60)) < 0.01

    # Gonzalo Montiel came on at 90:00 (records out of order in the
    # source); Marcos Acuna came on at 63:51.
    assert abs(by_id[28263].minutes_played - (FINAL_MATCH_END - 90)) < 0.01
    assert abs(by_id[19597].minutes_played - (FINAL_MATCH_END - (63 + 51 / 60))) < 0.01

    # Unused substitutes have no position records.
    assert by_id[3379].minutes_played == 0


def test_parse_lineups_uses_real_match_end_for_regular_time() -> None:
    appearances = parse_lineups(
        _load_fixture("lineups_3857276.json"), _load_fixture("events_3857276.json")
    )
    by_id = {a.statsbomb_player_id: a for a in appearances}

    # 3857276's second half ends at 93:54 in the real events.
    assert abs(by_id[6301].minutes_played - (93 + 54 / 60)) < 0.01
