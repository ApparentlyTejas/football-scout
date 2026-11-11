# StatsBomb Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up PostgreSQL + a minimal schema, ingest real match data from StatsBomb Open Data (free, no API key) for one competition/season, and expose the ingested players through a paginated FastAPI endpoint.

**Architecture:** Follows the guide's layered backend (API → Service → Repository → Database) and per-source adapter pattern. A pure HTTP client fetches raw StatsBomb JSON, a pure parser turns it into typed dataclasses, an ingestion service upserts those into PostgreSQL via repositories, and a thin API layer reads players back out. No Celery/Redis yet — StatsBomb Open Data is static and unrated-limited, so a one-shot CLI script is sufficient until a recurring-job need actually exists (Global Constraints).

**Tech Stack:** Python, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (via Docker Compose), `requests`, Pytest, SQLite (in-memory, for fast unit tests).

**Spec:** `PROJECT_GUIDE.md` (sections 3.2, 7-11, 31, 33, 43-44, 53, Rules 1-9) — this plan implements Phase 2 (Database) + Phase 3 (Data Ingestion, StatsBomb only) + a slice of Phase 5 (minimal Player API) from the guide's phase list. API-Football ingestion, feature engineering (per-90/percentiles), the baseline scout, ML, tactical fit, similarity, AI, and the frontend are each separate later plans — do not pull them into this one (Rule 1: implement one phase at a time).

**Verified against the live source (2026-11-11):** `https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json`, `.../matches/43/106.json`, `.../lineups/3857276.json`, `.../events/3857276.json` all return real data today. Pilot dataset: **FIFA World Cup 2022**, `competition_id=43`, `season_id=106` (64 matches). Confirmed event `type.name` values include `Pass`, `Shot`, `Carry`, `Pressure`, `Ball Recovery`, `Duel`, `Interception`, `Dribble`, `Miscontrol`, `Dispossessed`. A `Pass` event is incomplete iff `event["pass"].get("outcome")` is present (e.g. `{"name": "Incomplete"}`); absent means completed. A `Duel` event's subtype is `event["duel"]["type"]["name"]` (e.g. `"Aerial Lost"`, `"Aerial Won"`).

## Global Constraints

- $0 development/data cost (section 2) — StatsBomb Open Data only, no paid APIs, no API-Football in this plan.
- Never invent missing data (section 9) — StatsBomb lineups do not include date_of_birth, market_value, height, or contract_expiry; these columns stay `NULL` until a source that provides them is ingested.
- Never assume IDs from different providers are interchangeable (section 11) — all StatsBomb IDs are stored only in `player_external_ids` (source=`statsbomb`) and the internal `players.id` is a separate auto-generated key.
- Keep API versioning from the beginning: `/api/v1/` (section 31).
- Never commit secrets; `.env.example` stays in sync with any new env var (section 44).
- Each pipeline step should be independently executable (section 10) — client, parser, and ingestion service are each callable and testable on their own.
- Keep layers separate: API → Service → Repository → Database (section 53).
- Do not introduce new infrastructure unless necessary (Rule 3) — no Celery/Redis in this plan.

## Review Focus

- A single match fetch failing (network error or unexpected 404) must not abort ingestion of the rest of the competition/season batch — tested in Task 7.
- An event `type.name` the parser doesn't recognize must be skipped, not raise — tested in Task 5.
- A duplicate `(source, external_id)` pair in `player_external_ids` must be rejected by a DB constraint, not silently create a second internal player — tested in Task 2.
- `GET /api/v1/players` must paginate (`limit`/`offset`) instead of returning an unbounded result set — tested in Task 8.
- A player listed in a match's lineup but with zero recorded events (e.g. an unused substitute) must still get a `player_match_stats` row with zero counts and correct `minutes_played`, not be dropped — tested in Task 6.

---

## File Structure

New:
- `docker-compose.yml` — `postgres` + `backend` services
- `backend/Dockerfile`
- `backend/app/core/db.py` — engine, `SessionLocal`, `get_db` dependency
- `backend/app/models/base.py` — `Base` (`DeclarativeBase`)
- `backend/app/models/competition.py`, `season.py`, `team.py`, `player.py`, `player_external_id.py`, `match.py`, `player_match_stat.py`
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial_schema.py`
- `backend/app/services/ingestion/statsbomb_client.py` — pure HTTP fetch functions
- `backend/app/services/ingestion/statsbomb_parser.py` — pure parse functions and dataclasses
- `backend/app/services/ingestion/statsbomb_ingestion_service.py` — orchestration + upserts
- `backend/app/repositories/competition_repository.py`, `season_repository.py`, `team_repository.py`, `player_repository.py`, `match_repository.py`, `player_match_stat_repository.py`
- `scripts/ingest/ingest_statsbomb.py` — CLI entrypoint
- `backend/app/schemas/player.py`
- `backend/app/api/v1/endpoints/players.py`
- `backend/tests/conftest.py` — SQLite in-memory engine fixture, `TestClient` fixture
- `backend/tests/fixtures/statsbomb/lineups_3857276.json`, `backend/tests/fixtures/statsbomb/events_3857276.json` (trimmed real fixture data), `backend/tests/fixtures/statsbomb/match_3857276.json`
- `backend/tests/test_statsbomb_client.py`, `test_statsbomb_parser.py`, `test_statsbomb_ingestion_service.py`, `test_ingest_statsbomb_cli.py`, `test_players_api.py`

Modify:
- `backend/app/api/v1/router.py` — register players router
- `backend/requirements.txt` — add `requests`
- `.env.example` — no new vars needed (DATABASE_URL already present)

---

### Task 1: Docker Compose + PostgreSQL + DB session wiring

**Files:**
- Create: `docker-compose.yml`, `backend/Dockerfile`, `backend/app/core/db.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `backend.app.core.db.engine` (SQLAlchemy `Engine`, built from `settings.database_url`), `get_db() -> Generator[Session, None, None]` (FastAPI dependency), `SessionLocal` (sessionmaker).

- [ ] **Step 1: Write `docker-compose.yml`** with services `postgres` (image `postgres:16-alpine`, env `POSTGRES_DB=football_scout`, `POSTGRES_USER=football_scout`, `POSTGRES_PASSWORD=football_scout`, volume for data, port `5432:5432`) and `backend` (build from `backend/Dockerfile`, depends_on `postgres`, env `DATABASE_URL=postgresql://football_scout:football_scout@postgres:5432/football_scout`, port `8000:8000`).
- [ ] **Step 2: Write `backend/Dockerfile`** — `python:3.12-slim` base, copy `requirements.txt`, `pip install`, copy `app/`, `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
- [ ] **Step 3: Implement `backend/app/core/db.py`** with `engine = create_engine(settings.database_url, pool_pre_ping=True)`, `SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)`, and `get_db()` yielding a session and closing it in a `finally`.
- [ ] **Step 4: Write `backend/tests/test_db.py::test_get_db_yields_working_session`** — monkeypatch `settings.database_url` to `sqlite:///:memory:`, re-create an engine/session the same way `db.py` does, call `get_db()`, execute `SELECT 1` on the yielded session, assert it returns `1`.
- [ ] **Step 5: Run `pytest backend/tests/test_db.py -v`** — expect PASS.
- [ ] **Step 6: Manual verification** — run `docker compose up -d postgres` then `docker compose exec -T postgres pg_isready -U football_scout`. Expected output contains `accepting connections`. Run `docker compose down`.
- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml backend/Dockerfile backend/app/core/db.py backend/tests/test_db.py
git commit -m "feat: add docker-compose postgres service and DB session wiring"
```

---

### Task 2: SQLAlchemy models

**Files:**
- Create: `backend/app/models/base.py`, `competition.py`, `season.py`, `team.py`, `player.py`, `player_external_id.py`, `match.py`, `player_match_stat.py`
- Modify: `backend/app/models/__init__.py` (export all models so Alembic autogeneration sees them)
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Base` (declarative base, used by Task 3's Alembic `env.py`); ORM classes `Competition(id, statsbomb_competition_id unique, name, country, gender)`, `Season(id, competition_id FK, statsbomb_season_id, name)` with a unique constraint on `(competition_id, statsbomb_season_id)`, `Team(id, name, country)`, `Player(id, name, date_of_birth nullable, nationality nullable, primary_position nullable, market_value nullable, contract_expiry nullable, height nullable)`, `PlayerExternalId(id, player_id FK, source, external_id)` with a unique constraint on `(source, external_id)`, `Match(id, statsbomb_match_id unique, season_id FK, home_team_id FK, away_team_id FK, match_date, home_score, away_score)`, `PlayerMatchStat(id, player_id FK, match_id FK, team_id FK, minutes_played, passes_attempted, passes_completed, shots, carries, pressures, interceptions, ball_recoveries, dribbles, duels, aerial_duels, dispossessed, miscontrols)` with a unique constraint on `(player_id, match_id)`.

- [ ] **Step 1: Write `backend/tests/test_models.py::test_unique_constraint_on_player_external_id`** — build an in-memory SQLite engine, `Base.metadata.create_all(engine)`, insert a `Player` + one `PlayerExternalId(source="statsbomb", external_id="123")`, then attempt to insert a second `PlayerExternalId` with the same `(source, external_id)` pointing at a different player, assert it raises `IntegrityError`.
- [ ] **Step 2: Write `backend/tests/test_models.py::test_player_match_stat_round_trip`** — insert one of each model (`Competition`, `Season`, `Team`×2, `Player`, `Match`, `PlayerMatchStat`) with realistic values, query `PlayerMatchStat` back by `player_id`, assert every numeric field round-trips exactly.
- [ ] **Step 3: Run `pytest backend/tests/test_models.py -v`** — expect FAIL (modules don't exist yet).
- [ ] **Step 4: Implement `base.py`** (`class Base(DeclarativeBase): pass`) and the seven model files per the signatures above, using SQLAlchemy 2.0 `Mapped`/`mapped_column` style. Nullable columns use `Optional[...]`. Add the two unique constraints via `UniqueConstraint` in each model's `__table_args__`.
- [ ] **Step 5: Update `backend/app/models/__init__.py`** to import every model class (so `Base.metadata` is fully populated when something does `from app.models import *` or `import app.models`).
- [ ] **Step 6: Run `pytest backend/tests/test_models.py -v`** — expect PASS.
- [ ] **Step 7: Commit**

```bash
git add backend/app/models backend/tests/test_models.py
git commit -m "feat: add core SQLAlchemy models for competitions, matches, and player stats"
```

---

### Task 3: Alembic setup + initial migration

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial_schema.py`
- Modify: `backend/requirements.txt` (alembic already present)

**Interfaces:**
- Consumes: `app.models.base.Base`, `app.core.config.settings.database_url`.
- Produces: a runnable `alembic upgrade head` that creates every Task 2 table in a real PostgreSQL database.

- [ ] **Step 1: Run `cd backend && alembic init alembic`** to scaffold `alembic.ini` and `alembic/env.py`.
- [ ] **Step 2: Edit `backend/alembic/env.py`** — import `app.models` (to populate `Base.metadata`) and `app.core.db.Base`, set `target_metadata = Base.metadata`, and override `sqlalchemy.url` at runtime from `settings.database_url` instead of the static `alembic.ini` value.
- [ ] **Step 3: Run `cd backend && alembic revision --autogenerate -m "initial schema"`** to generate `0001_initial_schema.py`. Open the generated file and confirm it creates all seven tables with the two unique constraints from Task 2; fix anything autogenerate missed.
- [ ] **Step 4: Manual verification** — `docker compose up -d postgres`, then `cd backend && DATABASE_URL=postgresql://football_scout:football_scout@localhost:5432/football_scout alembic upgrade head`. Then `docker compose exec -T postgres psql -U football_scout -d football_scout -c '\dt'`. Expected output lists `competitions`, `seasons`, `teams`, `players`, `player_external_ids`, `matches`, `player_match_stats`.
- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic
git commit -m "feat: add alembic migrations for initial schema"
```

---

### Task 4: StatsBomb HTTP client

**Files:**
- Create: `backend/app/services/ingestion/statsbomb_client.py`
- Test: `backend/tests/test_statsbomb_client.py`

**Interfaces:**
- Produces: `fetch_competitions() -> list[dict]`, `fetch_matches(competition_id: int, season_id: int) -> list[dict]`, `fetch_lineups(match_id: int) -> list[dict]`, `fetch_events(match_id: int) -> list[dict]`, and `class StatsBombFetchError(Exception)` raised on non-200 responses.
- Base URL constant: `https://raw.githubusercontent.com/statsbomb/open-data/master/data`.

- [ ] **Step 1: Write `backend/tests/test_statsbomb_client.py::test_fetch_matches_builds_correct_url_and_returns_json`** — monkeypatch `requests.get` to a fake that asserts the URL equals `f"{BASE_URL}/matches/43/106.json"` and returns a response object whose `.json()` returns `[{"match_id": 1}]` and `.status_code == 200`; assert `fetch_matches(43, 106) == [{"match_id": 1}]`.
- [ ] **Step 2: Write `backend/tests/test_statsbomb_client.py::test_fetch_events_raises_on_404`** — monkeypatch `requests.get` to return `status_code=404`; assert `fetch_events(999999)` raises `StatsBombFetchError`.
- [ ] **Step 3: Run `pytest backend/tests/test_statsbomb_client.py -v`** — expect FAIL (module doesn't exist).
- [ ] **Step 4: Implement `statsbomb_client.py`** with the four functions above, each doing `requests.get(url, timeout=10)`, raising `StatsBombFetchError(f"StatsBomb fetch failed: {url} ({response.status_code})")` when `status_code != 200`, else returning `response.json()`.
- [ ] **Step 5: Run `pytest backend/tests/test_statsbomb_client.py -v`** — expect PASS.
- [ ] **Step 6: Add `requests` to `backend/requirements.txt`.**
- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ingestion/statsbomb_client.py backend/tests/test_statsbomb_client.py backend/requirements.txt
git commit -m "feat: add StatsBomb open-data HTTP client"
```

---

### Task 5: StatsBomb parser

**Files:**
- Create: `backend/app/services/ingestion/statsbomb_parser.py`
- Create (fixtures, trimmed from the real verified match `3857276`): `backend/tests/fixtures/statsbomb/lineups_3857276.json` (both teams, full player lists), `backend/tests/fixtures/statsbomb/events_3857276.json` (a trimmed subset: keep all events for 2-3 players across a few event types so exact counts are known, rather than all 3388 events)
- Test: `backend/tests/test_statsbomb_parser.py`

**Interfaces:**
- Consumes: raw dicts shaped like the JSON Task 4 fetches.
- Produces: `@dataclass ParsedPlayerAppearance(statsbomb_player_id: int, name: str, nationality: str | None, team_statsbomb_id: int, team_name: str, minutes_played: float)`; `@dataclass ParsedMatchPlayerStats(statsbomb_player_id: int, passes_attempted: int, passes_completed: int, shots: int, carries: int, pressures: int, interceptions: int, ball_recoveries: int, dribbles: int, duels: int, aerial_duels: int, dispossessed: int, miscontrols: int)`; `parse_lineups(lineups_json: list[dict]) -> list[ParsedPlayerAppearance]`; `parse_events(events_json: list[dict]) -> dict[int, ParsedMatchPlayerStats]` (keyed by `statsbomb_player_id`).

- [ ] **Step 1: Build the trimmed fixtures** — from the live `lineups/3857276.json` and `events/3857276.json`, write a small script or one-off snippet to keep both teams' full lineups (small, ~26 players × 2) and filter events down to only those belonging to 2-3 chosen players (e.g. `player.id == 6301` for Youssef En-Nesyri) across at least `Pass` (one complete, one incomplete), `Shot`, `Duel` (one `Aerial Won`, one `Aerial Lost`), `Interception`, and one unrecognized/irrelevant type like `Half Start` to prove it's skipped. Save as the two fixture files.
- [ ] **Step 2: Write `test_statsbomb_parser.py::test_parse_lineups_returns_all_players_with_minutes`** — load the lineups fixture, call `parse_lineups`, assert the returned list length equals total players across both teams, and assert a known starting player who played the full match has `minutes_played` close to `90` (within a documented tolerance, e.g. `±1`) while a known substitute who entered late has a smaller value derived from their `positions[].from`/`to`.
- [ ] **Step 3: Write `test_statsbomb_parser.py::test_parse_events_counts_known_player_correctly`** — load the trimmed events fixture, call `parse_events`, assert the entry for `player_id=6301` has exactly the counts built into the fixture (e.g. `passes_attempted=2, passes_completed=1, shots=1, duels=2, aerial_duels=2`).
- [ ] **Step 4: Write `test_statsbomb_parser.py::test_parse_events_ignores_unknown_event_types`** — assert that including a `Half Start` (or any type not in the known counter set) event for a player does not raise and does not get counted toward any field.
- [ ] **Step 5: Run `pytest backend/tests/test_statsbomb_parser.py -v`** — expect FAIL (module doesn't exist).
- [ ] **Step 6: Implement `statsbomb_parser.py`.** `parse_lineups` iterates each team's `lineup`, and for each player sums `(to - from)` in minutes across `positions` (parsing `mm:ss`/`hh:mm:ss` strings; when a position's `to` is `None`, treat it as running to the end of that `period`'s known duration from the last event minute seen, or simply to `90` for period 2 / `45` for period 1 if no further information is available — document this approximation in a comment). `parse_events` iterates the flat event list, and for each event looks up `event["player"]["id"]` (skip events with no `player` key, e.g. team-level events) and increments the matching counter in that player's `ParsedMatchPlayerStats` based on `event["type"]["name"]`: `Pass` → `passes_attempted` always, `passes_completed` when `"outcome" not in event.get("pass", {})`; `Shot` → `shots`; `Carry` → `carries`; `Pressure` → `pressures`; `Interception` → `interceptions`; `Ball Recovery` → `ball_recoveries`; `Dribble` → `dribbles`; `Duel` → `duels`, and additionally `aerial_duels` when `event["duel"]["type"]["name"].startswith("Aerial")`; `Dispossessed` → `dispossessed`; `Miscontrol` → `miscontrols`. Any other `type.name` is a no-op (the `else` branch of a lookup, not a raise).
- [ ] **Step 7: Run `pytest backend/tests/test_statsbomb_parser.py -v`** — expect PASS.
- [ ] **Step 8: Commit**

```bash
git add backend/app/services/ingestion/statsbomb_parser.py backend/tests/test_statsbomb_parser.py backend/tests/fixtures/statsbomb
git commit -m "feat: add StatsBomb lineup and event parser"
```

---

### Task 6: Repositories + ingestion service

**Files:**
- Create: `backend/app/repositories/competition_repository.py`, `season_repository.py`, `team_repository.py`, `player_repository.py`, `match_repository.py`, `player_match_stat_repository.py`, `backend/app/services/ingestion/statsbomb_ingestion_service.py`
- Test: `backend/tests/test_statsbomb_ingestion_service.py`

**Interfaces:**
- Consumes: `ParsedPlayerAppearance`, `ParsedMatchPlayerStats` (Task 5); `Competition`, `Season`, `Team`, `Player`, `PlayerExternalId`, `Match`, `PlayerMatchStat` (Task 2); a SQLAlchemy `Session`.
- Produces: each repository exposes a `get_or_create_*(session, ...) -> Model` function (e.g. `get_or_create_team(session: Session, name: str, country: str | None) -> Team`); `ingest_match(session: Session, competition: dict, season: dict, match_json: dict, lineups_json: list[dict], events_json: list[dict]) -> Match` — the single entry point later tasks call, which upserts everything for one match and is safe to call twice with the same inputs (no duplicate rows, values overwritten to match the latest input).

- [ ] **Step 1: Write `test_statsbomb_ingestion_service.py::test_ingest_match_creates_expected_rows`** — using an in-memory SQLite session, call `ingest_match` once with the Task 5 fixtures (plus a small hand-built `match_json` dict for match `3857276`), then assert: one `Match` row exists with the right `statsbomb_match_id`; the number of `Player` rows equals the number of distinct players in the lineups fixture; the number of `PlayerMatchStat` rows equals that same count (including players with zero events); and the player with known event counts (Task 5, player `6301`) has a `PlayerMatchStat` row whose fields match exactly.
- [ ] **Step 2: Write `test_statsbomb_ingestion_service.py::test_ingest_match_is_idempotent`** — call `ingest_match` twice with identical inputs, assert the row counts for every table are unchanged between the two calls (no duplicates).
- [ ] **Step 3: Write `test_statsbomb_ingestion_service.py::test_player_with_zero_events_still_gets_a_stats_row`** — using a lineup fixture player who has no events in the trimmed events fixture, assert their `PlayerMatchStat` row exists with every counter at `0` and a non-null `minutes_played`.
- [ ] **Step 4: Run `pytest backend/tests/test_statsbomb_ingestion_service.py -v`** — expect FAIL.
- [ ] **Step 5: Implement the six repository files**, each a thin `get_or_create_x(session, lookup_kwargs, defaults) -> Model` using `session.execute(select(Model).where(...)).scalar_one_or_none()` then insert-if-missing, and `upsert_player_match_stat(session, player_id, match_id, team_id, stats: ParsedMatchPlayerStats | None, minutes_played)` that updates-in-place if a row for `(player_id, match_id)` exists.
- [ ] **Step 6: Implement `statsbomb_ingestion_service.ingest_match`**: get-or-create the `Competition`/`Season`/both `Team`s/`Match`; call `parse_lineups` and `parse_events`; for each parsed appearance, get-or-create the `Player` by matching through `PlayerExternalId(source="statsbomb", external_id=str(statsbomb_player_id))` (create the `Player` + external-id row together if missing), then call `upsert_player_match_stat` with that player's parsed stats (or all-zero stats if the player has no entry in the events dict).
- [ ] **Step 7: Run `pytest backend/tests/test_statsbomb_ingestion_service.py -v`** — expect PASS.
- [ ] **Step 8: Commit**

```bash
git add backend/app/repositories backend/app/services/ingestion/statsbomb_ingestion_service.py backend/tests/test_statsbomb_ingestion_service.py
git commit -m "feat: add repositories and StatsBomb match ingestion service"
```

---

### Task 7: Ingestion CLI script

**Files:**
- Create: `scripts/ingest/ingest_statsbomb.py`
- Test: `backend/tests/test_ingest_statsbomb_cli.py`

**Interfaces:**
- Consumes: `fetch_competitions`, `fetch_matches`, `fetch_lineups`, `fetch_events` (Task 4), `ingest_match` (Task 6), `SessionLocal` (Task 1).
- Produces: `run_ingestion(session: Session, competition_id: int, season_id: int, limit: int | None = None) -> IngestionSummary` where `IngestionSummary` is a `@dataclass(matches_attempted: int, matches_ingested: int, matches_failed: int)`; a `if __name__ == "__main__":` CLI with `argparse` flags `--competition-id` (default `43`), `--season-id` (default `106`), `--limit` (default `None`).

- [ ] **Step 1: Write `test_ingest_statsbomb_cli.py::test_run_ingestion_continues_after_one_match_fetch_fails`** — monkeypatch `fetch_matches` to return two match stubs, monkeypatch `fetch_lineups`/`fetch_events` so the first match's call raises `StatsBombFetchError` and the second succeeds (using Task 5's fixtures), call `run_ingestion`, assert `matches_attempted == 2`, `matches_failed == 1`, `matches_ingested == 1`, and that the second match's data did make it into the DB.
- [ ] **Step 2: Write `test_ingest_statsbomb_cli.py::test_run_ingestion_respects_limit`** — monkeypatch `fetch_matches` to return 5 match stubs, call `run_ingestion(..., limit=2)`, assert `matches_attempted == 2`.
- [ ] **Step 3: Run `pytest backend/tests/test_ingest_statsbomb_cli.py -v`** — expect FAIL.
- [ ] **Step 4: Implement `run_ingestion`** — fetch the matches list, optionally slice to `limit`, and for each match: fetch its lineups and events, wrap the `fetch_*` + `ingest_match` calls for that single match in a `try/except StatsBombFetchError`, incrementing `matches_failed` on exception (logging the match id and error) and `matches_ingested` on success, always incrementing `matches_attempted`. Implement the `argparse` CLI wrapper that builds a `SessionLocal()` session, calls `run_ingestion`, prints the summary, and commits (or rolls back on an unhandled exception).
- [ ] **Step 5: Run `pytest backend/tests/test_ingest_statsbomb_cli.py -v`** — expect PASS.
- [ ] **Step 6: Manual verification (real network + real Postgres)** — `docker compose up -d postgres`, `cd backend && DATABASE_URL=postgresql://football_scout:football_scout@localhost:5432/football_scout python ../scripts/ingest/ingest_statsbomb.py --limit 1`. Expected: prints a summary with `matches_ingested=1`, and `docker compose exec -T postgres psql -U football_scout -d football_scout -c 'SELECT count(*) FROM players;'` returns a count greater than 0.
- [ ] **Step 7: Commit**

```bash
git add scripts/ingest/ingest_statsbomb.py backend/tests/test_ingest_statsbomb_cli.py
git commit -m "feat: add StatsBomb ingestion CLI script"
```

---

### Task 8: Player API

**Files:**
- Create: `backend/app/schemas/player.py`, `backend/app/api/v1/endpoints/players.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_players_api.py`

**Interfaces:**
- Consumes: `Player`, `PlayerMatchStat` models (Task 2); `get_db` (Task 1).
- Produces: Pydantic `PlayerOut(id: int, name: str, nationality: str | None, primary_position: str | None)` (`model_config = ConfigDict(from_attributes=True)`); `GET /api/v1/players?limit=&offset=` → `list[PlayerOut]` (default `limit=50`, max `limit=200`, default `offset=0`); `GET /api/v1/players/{player_id}` → `PlayerOut` or `404`.

- [ ] **Step 1: Write `test_players_api.py::test_list_players_paginates`** — seed the test SQLite DB (via the `conftest.py` fixture) with 3 players, call `GET /api/v1/players?limit=2&offset=0`, assert the response has exactly 2 items; call again with `offset=2`, assert exactly 1 item.
- [ ] **Step 2: Write `test_players_api.py::test_get_player_by_id_returns_404_for_missing`** — call `GET /api/v1/players/999999`, assert status `404` and that the JSON body does not contain a stack trace (just a `detail` string).
- [ ] **Step 3: Write `test_players_api.py::test_get_player_by_id_returns_player`** — seed one player, `GET /api/v1/players/{id}`, assert the returned JSON matches the seeded name/nationality.
- [ ] **Step 4: Run `pytest backend/tests/test_players_api.py -v`** — expect FAIL.
- [ ] **Step 5: Implement `schemas/player.py`** (`PlayerOut` as above) **and `api/v1/endpoints/players.py`** with the two routes, using `Depends(get_db)` and the `Player` repository's `get_or_create`-adjacent read helpers (add a plain `list_players(session, limit, offset)` and `get_player(session, player_id)` to `player_repository.py` if not already present from Task 6).
- [ ] **Step 6: Register the router** in `backend/app/api/v1/router.py` (`api_router.include_router(players_router, prefix="/players", tags=["players"])`).
- [ ] **Step 7: Run `pytest backend/tests/test_players_api.py -v`** — expect PASS.
- [ ] **Step 8: Run the full backend test suite**: `cd backend && pytest -v` — expect all PASS.
- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/player.py backend/app/api/v1/endpoints/players.py backend/app/api/v1/router.py backend/app/repositories/player_repository.py backend/tests/test_players_api.py
git commit -m "feat: add paginated player list and detail API endpoints"
```

---

## Phase Boundary

This plan stops once a user can run the ingestion script against FIFA World Cup 2022 and query the resulting players through `GET /api/v1/players`. The next plan (feature engineering: per-90 stats, percentiles, position-group normalization — guide Phase 4) builds on top of `player_match_stats`, not alongside it, and should be written after this one is merged and verified end-to-end.
