"""CLI entry point that ingests a full StatsBomb competition/season.

Loops over every match StatsBomb's open-data `matches/<competition>/<season>.json`
lists, fetching each match's lineups and events and handing them to Task 6's
`ingest_match`. A single match's fetch failure (StatsBomb open-data is a static
GitHub mirror and some match ids 404) is logged and counted rather than
aborting the whole run.
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import Session  # noqa: E402

from app.services.ingestion.statsbomb_client import (  # noqa: E402
    StatsBombFetchError,
    fetch_competitions,
    fetch_events,
    fetch_lineups,
    fetch_matches,
)
from app.services.ingestion.statsbomb_ingestion_service import ingest_match  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass
class IngestionSummary:
    matches_attempted: int = 0
    matches_ingested: int = 0
    matches_failed: int = 0


def _find_competition_and_season(competition_id: int, season_id: int) -> tuple[dict, dict]:
    """Look up the competition/season pair in `fetch_competitions()`'s list
    and reshape it into the `competition`/`season` dicts `ingest_match`
    expects."""
    for entry in fetch_competitions():
        if entry["competition_id"] == competition_id and entry["season_id"] == season_id:
            competition = {
                "statsbomb_competition_id": entry["competition_id"],
                "name": entry["competition_name"],
                "country": entry["country_name"],
                "gender": entry["competition_gender"],
            }
            season = {
                "statsbomb_season_id": entry["season_id"],
                "name": entry["season_name"],
            }
            return competition, season

    raise StatsBombFetchError(
        f"No competition/season entry found for competition_id={competition_id}, "
        f"season_id={season_id}"
    )


def run_ingestion(
    session: Session,
    competition_id: int,
    season_id: int,
    limit: int | None = None,
) -> IngestionSummary:
    competition, season = _find_competition_and_season(competition_id, season_id)

    matches = fetch_matches(competition_id, season_id)
    if limit is not None:
        matches = matches[:limit]

    summary = IngestionSummary()

    for match_json in matches:
        summary.matches_attempted += 1
        match_id = match_json["match_id"]
        try:
            lineups_json = fetch_lineups(match_id)
            events_json = fetch_events(match_id)
            ingest_match(
                session=session,
                competition=competition,
                season=season,
                match_json=match_json,
                lineups_json=lineups_json,
                events_json=events_json,
            )
        except StatsBombFetchError as exc:
            logger.error("Failed to ingest match %s: %s", match_id, exc)
            summary.matches_failed += 1
        else:
            summary.matches_ingested += 1

    return summary
