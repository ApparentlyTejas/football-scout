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


def test_parse_events_counts_known_player_correctly() -> None:
    events_json = _load_fixture("events_3857276.json")

    stats = parse_events(events_json)

    en_nesyri_stats = stats[6301]
    assert en_nesyri_stats.passes_attempted == 2
    assert en_nesyri_stats.passes_completed == 1
    assert en_nesyri_stats.shots == 1
    assert en_nesyri_stats.duels == 2
    assert en_nesyri_stats.aerial_duels == 2
    assert en_nesyri_stats.interceptions == 1
    assert en_nesyri_stats.carries == 0
    assert en_nesyri_stats.pressures == 0
    assert en_nesyri_stats.ball_recoveries == 0
    assert en_nesyri_stats.dribbles == 0
    assert en_nesyri_stats.dispossessed == 0
    assert en_nesyri_stats.miscontrols == 0

    boufal_stats = stats[3625]
    assert boufal_stats.carries == 1
    assert boufal_stats.ball_recoveries == 1
    assert boufal_stats.passes_attempted == 0


def test_parse_events_ignores_unknown_event_types() -> None:
    events_json = _load_fixture("events_3857276.json")

    # The fixture includes a team-level "Half Start" event with no
    # "player" key at all, proving the parser skips it without raising.
    stats = parse_events(events_json)

    # Exactly the two players with real events show up; the player-less
    # "Half Start" event produced no entry and did not crash the parser.
    assert set(stats.keys()) == {6301, 3625}
