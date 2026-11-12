"""Single entry point that ingests one StatsBomb match into the database.

Ties together the Task 4 fetch layer's JSON shapes (consumed here as plain
dicts, so this module has no HTTP dependency of its own), the Task 5
parser, and the Task 6 repositories into one idempotent call: running
`ingest_match` twice with the same inputs upserts in place rather than
creating duplicate rows.
"""

import datetime

from sqlalchemy.orm import Session

from app.models.match import Match
from app.repositories.competition_repository import get_or_create_competition
from app.repositories.match_repository import get_or_create_match
from app.repositories.player_match_stat_repository import upsert_player_match_stat
from app.repositories.player_repository import get_or_create_player
from app.repositories.season_repository import get_or_create_season
from app.repositories.team_repository import get_or_create_team
from app.services.ingestion.statsbomb_parser import parse_events, parse_lineups


def ingest_match(
    session: Session,
    competition: dict,
    season: dict,
    match_json: dict,
    lineups_json: list[dict],
    events_json: list[dict],
) -> Match:
    """Upsert one StatsBomb match and everything it references (its
    competition, season, both teams, the match row itself, every player
    who appeared in the lineups, and each player's match stats) in a
    single call.

    `competition` is `{"statsbomb_competition_id", "name", "country",
    "gender"}`; `season` is `{"statsbomb_season_id", "name"}` (its
    `competition_id` is resolved here from the competition just
    upserted); `match_json` mirrors StatsBomb's `matches/<comp>/<season>.json`
    entry shape: `{"match_id", "match_date", "home_team":
    {"home_team_id", "home_team_name"}, "away_team": {"away_team_id",
    "away_team_name"}, "home_score", "away_score"}`.
    """
    competition_row = get_or_create_competition(
        session,
        statsbomb_competition_id=competition["statsbomb_competition_id"],
        name=competition["name"],
        country=competition["country"],
        gender=competition["gender"],
    )

    season_row = get_or_create_season(
        session,
        competition_id=competition_row.id,
        statsbomb_season_id=season["statsbomb_season_id"],
        name=season["name"],
    )

    home_team_json = match_json["home_team"]
    away_team_json = match_json["away_team"]

    home_team = get_or_create_team(
        session,
        name=home_team_json["home_team_name"],
        country=None,
    )
    away_team = get_or_create_team(
        session,
        name=away_team_json["away_team_name"],
        country=None,
    )

    match_date = match_json["match_date"]
    if isinstance(match_date, str):
        match_date = datetime.date.fromisoformat(match_date)

    match_row = get_or_create_match(
        session,
        statsbomb_match_id=match_json["match_id"],
        season_id=season_row.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        match_date=match_date,
        home_score=match_json["home_score"],
        away_score=match_json["away_score"],
    )

    appearances = parse_lineups(lineups_json)
    stats_by_player = parse_events(events_json)

    # StatsBomb's lineup team ids are the same ids used for home/away
    # above, so appearances can be routed to the right Team row without a
    # third get_or_create_team call.
    team_by_statsbomb_id = {
        home_team_json["home_team_id"]: home_team,
        away_team_json["away_team_id"]: away_team,
    }

    for appearance in appearances:
        player_row = get_or_create_player(
            session,
            statsbomb_player_id=appearance.statsbomb_player_id,
            name=appearance.name,
            nationality=appearance.nationality,
        )

        team = team_by_statsbomb_id[appearance.team_statsbomb_id]
        parsed_stats = stats_by_player.get(appearance.statsbomb_player_id)

        upsert_player_match_stat(
            session,
            player_id=player_row.id,
            match_id=match_row.id,
            team_id=team.id,
            stats=parsed_stats,
            minutes_played=appearance.minutes_played,
        )

    return match_row
