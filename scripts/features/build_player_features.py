"""CLI entry point that builds one season's player_season_stats rows from
already-ingested PlayerMatchStat data.
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import SessionLocal  # noqa: E402
from app.services.features.player_season_stats_builder import build_season_features  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    arg_parser = argparse.ArgumentParser(
        description="Build per-season player features from ingested StatsBomb data."
    )
    arg_parser.add_argument("--season-id", type=int, required=True)
    args = arg_parser.parse_args(argv)

    session = SessionLocal()
    try:
        count = build_season_features(session, args.season_id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Processed {count} players for season {args.season_id}")


if __name__ == "__main__":
    main()
