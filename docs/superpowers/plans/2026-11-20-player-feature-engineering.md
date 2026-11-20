# Player Feature Engineering (Phase 4: Data Processing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the raw `player_match_stats` rows ingested by the StatsBomb pipeline into a per-season, per-player feature table of per-90 metrics and within-cohort percentiles, built by a reproducible CLI script.

**Architecture:** A pure aggregation module sums each player's `player_match_stats` rows for one season into per-90 rates (no DB access), a pure percentile module ranks those rates within `(season_id, position_group)` cohorts (no DB access), and a thin repository upserts the combined result into a new `player_season_stats` table. A CLI script (mirroring `scripts/ingest/ingest_statsbomb.py`) wires fetch → aggregate → percentile → upsert for one season at a time. No new HTTP calls or external data — this plan only processes what Phase 3 already stored.

**Tech Stack:** Python, SQLAlchemy 2.0, Alembic, PostgreSQL, Pytest, SQLite (in-memory, for fast unit tests). No new third-party dependencies — percentile ranking uses only the stdlib.

**Spec:** `PROJECT_GUIDE.md` (sections 11, 12, 14, Phase 4 at lines 1323-1338, Rules 1-9) — this plan implements Phase 4 (Data Processing) only: per-90 metrics, percentiles, and position groups, scoped to the stats StatsBomb ingestion already captures (no xG/xA/tackles — those fields don't exist in `player_match_stats` and must not be invented). Position-specific scoring weights (section 13), the player profile vector/embeddings (sections 15-16), and the Player Profile API (Phase 5) are separate later plans — do not pull them into this one.

## Global Constraints

- $0 development/data cost — no new external data sources or paid APIs in this plan.
- Never invent missing data (section 9) — only metrics derivable from existing `player_match_stats` columns are computed; a player with zero recorded minutes gets `NULL` per-90 fields, not a divide-by-zero or a fabricated `0.0`.
- Never assume IDs from different providers are interchangeable (section 11) — this plan only reads the internal `players.id`/`seasons.id`, never a raw StatsBomb id.
- Each pipeline step should be independently executable (section 10) — the aggregator and the percentile ranker are each pure functions, callable and testable without a database.
- Keep layers separate: Service (aggregation/percentiles) → Repository → Database.
- Do not introduce new infrastructure unless necessary (Rule 3) — no Celery/Redis; a one-shot CLI script is sufficient, matching the existing ingestion script.
- Document the normalization methodology (section 14) — the percentile formula and the minimum-minutes threshold are written down in the module docstring, not left implicit.

## Review Focus

- A player with `minutes_played == 0` for the season (an unused substitute across every match) must get `NULL` per-90 fields, not a `ZeroDivisionError` or a `0.0` that reads as "measured and found to be zero" — tested in Task 1.
- A cohort (`season_id`, `position_group`) with only one qualifying player must still produce a defined percentile (not raise, not divide by zero) — tested in Task 2.
- A player whose season minutes fall below the minimum-minutes threshold must get `NULL` percentile fields (excluded from ranking) even though their raw per-90 fields are still populated — tested in Task 2.
- A `Player.primary_position` value that isn't one of StatsBomb's canonical position names (or is `None`) must map to `position_group = None` rather than raising or silently joining the wrong cohort — tested in Task 1.
- Running the season build twice (same inputs) must update the existing `player_season_stats` rows in place, not create duplicates — tested in Task 4.

---

## File Structure

New:
- `backend/app/services/features/position_groups.py` — pure `map_position_to_group` function + canonical StatsBomb position map
- `backend/app/services/features/season_aggregator.py` — pure per-season raw-counter + per-90 aggregation from `PlayerMatchStat` rows
- `backend/app/services/features/percentiles.py` — pure within-cohort percentile ranking
- `backend/app/services/features/player_season_stats_builder.py` — orchestrates aggregator + percentiles + repository upsert for one season
- `backend/app/models/player_season_stat.py` — `PlayerSeasonStat` ORM model
- `backend/alembic/versions/0002_player_season_stats.py`
- `backend/app/repositories/player_season_stat_repository.py`
- `scripts/features/build_player_features.py` — CLI entrypoint
- `backend/tests/test_position_groups.py`, `test_season_aggregator.py`, `test_percentiles.py`, `test_player_season_stat_model.py`, `test_player_season_stats_builder.py`, `test_build_player_features_cli.py`

Modify:
- `backend/app/models/__init__.py` — export `PlayerSeasonStat`

---

### Task 1: Position groups + season aggregator

**Files:**
- Create: `backend/app/services/features/position_groups.py`, `backend/app/services/features/season_aggregator.py`
- Test: `backend/tests/test_position_groups.py`, `backend/tests/test_season_aggregator.py`

**Interfaces:**
- Consumes: `PlayerMatchStat`, `Player`, `Match` (existing models).
- Produces: `map_position_to_group(position: str | None) -> str | None`; `@dataclass PlayerSeasonAggregate(player_id: int, team_id: int, position_group: str | None, matches_played: int, minutes_played: int, passes_attempted: int, passes_completed: int, shots: int, carries: int, pressures: int, interceptions: int, ball_recoveries: int, dribbles: int, duels: int, aerial_duels: int, dispossessed: int, miscontrols: int, pass_completion_pct: float | None, passes_per_90: float | None, shots_per_90: float | None, carries_per_90: float | None, pressures_per_90: float | None, interceptions_per_90: float | None, ball_recoveries_per_90: float | None, dribbles_per_90: float | None, duels_per_90: float | None, aerial_duels_per_90: float | None, dispossessed_per_90: float | None, miscontrols_per_90: float | None)`; `aggregate_season(session: Session, season_id: int) -> list[PlayerSeasonAggregate]`.

- [ ] **Step 1: Write `test_position_groups.py::test_map_position_to_group_covers_all_canonical_statsbomb_positions`** — for each of the 25 canonical StatsBomb position names (`"Goalkeeper"`, `"Right Back"`, `"Right Center Back"`, `"Center Back"`, `"Left Center Back"`, `"Left Back"`, `"Right Wing Back"`, `"Left Wing Back"`, `"Right Defensive Midfield"`, `"Center Defensive Midfield"`, `"Left Defensive Midfield"`, `"Right Midfield"`, `"Right Center Midfield"`, `"Center Midfield"`, `"Left Center Midfield"`, `"Left Midfield"`, `"Right Wing"`, `"Right Attacking Midfield"`, `"Center Attacking Midfield"`, `"Left Attacking Midfield"`, `"Left Wing"`, `"Right Center Forward"`, `"Center Forward"`, `"Left Center Forward"`, `"Striker"`, `"Secondary Striker"`), assert `map_position_to_group` returns one of `{"GK", "CB", "FB", "DM", "CM", "AM", "WING", "FW"}` (never `None`).
- [ ] **Step 2: Write `test_position_groups.py::test_map_position_to_group_handles_unknown_and_none`** — assert `map_position_to_group(None) is None` and `map_position_to_group("Not A Real Position") is None`.
- [ ] **Step 3: Run `pytest backend/tests/test_position_groups.py -v`** — expect FAIL (module doesn't exist).
- [ ] **Step 4: Implement `position_groups.py`** with a `dict[str, str]` constant mapping each of the 25 names above to one of `GK` (Goalkeeper), `FB` (both full-back and wing-back names), `CB` (all three center-back names), `DM` (all three defensive-midfield names), `CM` (all five central/wide-midfield names), `AM` (all three attacking-midfield names), `WING` (`Right Wing`, `Left Wing`), `FW` (both center-forward names, `Striker`, `Secondary Striker`); `map_position_to_group` does a plain `.get(position)` returning `None` for `None` or an unrecognized string.
- [ ] **Step 5: Run `pytest backend/tests/test_position_groups.py -v`** — expect PASS.
- [ ] **Step 6: Write `test_season_aggregator.py::test_aggregate_season_sums_stats_and_computes_per_90`** — in an in-memory SQLite session, seed one `Season`/`Competition`, one `Team`, one `Player` (`primary_position="Center Forward"`), two `Match` rows in that season, and two `PlayerMatchStat` rows for that player (e.g. match 1: `minutes_played=45, shots=2, passes_attempted=10, passes_completed=8, ...`; match 2: `minutes_played=45, shots=1, passes_attempted=10, passes_completed=9, ...`). Call `aggregate_season(session, season_id)`, assert the single returned `PlayerSeasonAggregate` has `matches_played=2`, `minutes_played=90`, `shots=3`, `shots_per_90=3.0`, `passes_attempted=20`, `passes_completed=17`, `pass_completion_pct=85.0`, `position_group="FW"`.
- [ ] **Step 7: Write `test_season_aggregator.py::test_aggregate_season_handles_zero_minutes_player`** — seed a player whose only `PlayerMatchStat` row has `minutes_played=0` and all counters `0`, call `aggregate_season`, assert every `*_per_90` field and `pass_completion_pct` is `None` (not `0.0`, not a raised exception) while `minutes_played == 0` and `matches_played == 1`.
- [ ] **Step 8: Write `test_season_aggregator.py::test_aggregate_season_maps_unknown_position_to_none_group`** — seed a player with `primary_position=None`, assert the returned aggregate has `position_group=None`.
- [ ] **Step 9: Run `pytest backend/tests/test_season_aggregator.py -v`** — expect FAIL.
- [ ] **Step 10: Implement `season_aggregator.py`.** `aggregate_season` queries `PlayerMatchStat` joined to `Match` where `Match.season_id == season_id`, groups rows in Python by `player_id`, sums every raw counter and `minutes_played`, counts rows as `matches_played`, takes `team_id` from the most recent match (`Match.match_date`) for that player in the group, looks up `Player.primary_position` and maps it via `map_position_to_group`. `pass_completion_pct = passes_completed / passes_attempted * 100 if passes_attempted > 0 else None`. Each `*_per_90` field is `total * 90 / minutes_played if minutes_played > 0 else None`.
- [ ] **Step 11: Run `pytest backend/tests/test_season_aggregator.py -v`** — expect PASS.
- [ ] **Step 12: Commit**

```bash
git add backend/app/services/features/position_groups.py backend/app/services/features/season_aggregator.py backend/tests/test_position_groups.py backend/tests/test_season_aggregator.py
git commit -m "feat: add position-group mapping and per-season per-90 aggregator"
```

---

### Task 2: Percentile ranking

**Files:**
- Create: `backend/app/services/features/percentiles.py`
- Test: `backend/tests/test_percentiles.py`

**Interfaces:**
- Consumes: `PlayerSeasonAggregate` (Task 1).
- Produces: `MIN_MINUTES_FOR_PERCENTILE: int = 270`; `PER_90_FIELDS: tuple[str, ...]` (the 11 `*_per_90` field names plus `pass_completion_pct`, from Task 1's dataclass); `@dataclass PlayerSeasonPercentiles(player_id: int, <field>_percentile: float | None for each name in PER_90_FIELDS)`; `compute_percentile_rank(value: float, cohort_values: list[float]) -> float`; `compute_percentiles(aggregates: list[PlayerSeasonAggregate]) -> dict[int, PlayerSeasonPercentiles]` (keyed by `player_id`).

- [ ] **Step 1: Write `test_percentiles.py::test_compute_percentile_rank_formula`** — for `cohort_values = [1.0, 2.0, 3.0, 4.0]`, assert `compute_percentile_rank(1.0, cohort_values) == 12.5` (0 strictly below + 0.5 tie, over 4, times 100), `compute_percentile_rank(4.0, cohort_values) == 87.5`, `compute_percentile_rank(2.5, cohort_values) == 50.0`. Document this exact formula — `(count_strictly_below + 0.5 * count_equal) / n * 100` — in the module docstring as the chosen methodology (spec section 14).
- [ ] **Step 2: Write `test_percentiles.py::test_compute_percentile_rank_single_value_cohort`** — `compute_percentile_rank(5.0, [5.0]) == 50.0` (no division by zero, a lone player ranks at the middle).
- [ ] **Step 3: Write `test_percentiles.py::test_compute_percentiles_groups_by_season_and_position_group`** — build three `PlayerSeasonAggregate`s: two `FW`s with distinct `shots_per_90` and one `CM`, all with `minutes_played=900` (above threshold). Call `compute_percentiles`, assert the two `FW` players' `shots_per_90_percentile` are computed relative to each other only (not influenced by the `CM`'s value) and the `CM`'s `shots_per_90_percentile` is `50.0` (lone cohort member).
- [ ] **Step 4: Write `test_percentiles.py::test_compute_percentiles_excludes_players_below_minute_threshold`** — one aggregate with `minutes_played=100` (below `MIN_MINUTES_FOR_PERCENTILE`) and nonzero `shots_per_90`; assert its `PlayerSeasonPercentiles.shots_per_90_percentile is None`, and that it is excluded from the cohort used to rank other players (a second, qualifying player in the same `position_group` with the same `shots_per_90` value must get `50.0`, not a value skewed by the excluded player).
- [ ] **Step 5: Write `test_percentiles.py::test_compute_percentiles_handles_none_per_90_value`** — an aggregate with `minutes_played=900` but `shots_per_90=None` (shouldn't happen given Task 1's guard, but percentiles must not raise); assert `shots_per_90_percentile is None` for that player and that player is excluded from other players' cohort.
- [ ] **Step 6: Run `pytest backend/tests/test_percentiles.py -v`** — expect FAIL (module doesn't exist).
- [ ] **Step 7: Implement `percentiles.py`.** `compute_percentile_rank` counts `below`/`equal` over `cohort_values` and applies the Step 1 formula. `compute_percentiles` groups aggregates by `(position_group)` (season is already fixed — one season's aggregates are passed in per call), and for each of `PER_90_FIELDS`, builds the cohort from aggregates with `minutes_played >= MIN_MINUTES_FOR_PERCENTILE` and a non-`None` value for that field, then calls `compute_percentile_rank` for each qualifying player; non-qualifying players get `None` for every field.
- [ ] **Step 8: Run `pytest backend/tests/test_percentiles.py -v`** — expect PASS.
- [ ] **Step 9: Commit**

```bash
git add backend/app/services/features/percentiles.py backend/tests/test_percentiles.py
git commit -m "feat: add within-cohort percentile ranking for season aggregates"
```

---

### Task 3: `PlayerSeasonStat` model + migration

**Files:**
- Create: `backend/app/models/player_season_stat.py`, `backend/alembic/versions/0002_player_season_stats.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_player_season_stat_model.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2 directly (same field names, no import).
- Produces: `PlayerSeasonStat(id, player_id FK, season_id FK, team_id FK, position_group nullable, matches_played, minutes_played, passes_attempted, passes_completed, shots, carries, pressures, interceptions, ball_recoveries, dribbles, duels, aerial_duels, dispossessed, miscontrols, pass_completion_pct nullable, passes_per_90 nullable, shots_per_90 nullable, carries_per_90 nullable, pressures_per_90 nullable, interceptions_per_90 nullable, ball_recoveries_per_90 nullable, dribbles_per_90 nullable, duels_per_90 nullable, aerial_duels_per_90 nullable, dispossessed_per_90 nullable, miscontrols_per_90 nullable, pass_completion_pct_percentile nullable, passes_per_90_percentile nullable, shots_per_90_percentile nullable, carries_per_90_percentile nullable, pressures_per_90_percentile nullable, interceptions_per_90_percentile nullable, ball_recoveries_per_90_percentile nullable, dribbles_per_90_percentile nullable, duels_per_90_percentile nullable, aerial_duels_per_90_percentile nullable, dispossessed_per_90_percentile nullable, miscontrols_per_90_percentile nullable)` with a unique constraint on `(player_id, season_id)`.

- [ ] **Step 1: Write `test_player_season_stat_model.py::test_unique_constraint_on_player_season`** — in-memory SQLite, `Base.metadata.create_all`, insert one `PlayerSeasonStat` for `(player_id, season_id)`, attempt a second insert with the same pair, assert `IntegrityError`.
- [ ] **Step 2: Write `test_player_season_stat_model.py::test_player_season_stat_round_trip`** — insert one row with every field populated (including `None` for a couple of percentile fields), query it back, assert every field round-trips exactly.
- [ ] **Step 3: Run `pytest backend/tests/test_player_season_stat_model.py -v`** — expect FAIL (module doesn't exist).
- [ ] **Step 4: Implement `player_season_stat.py`** following the `PlayerMatchStat` model's style (`Mapped`/`mapped_column`, `Integer`/`Float`/`String` columns, `Optional[...]` for nullable ones, `UniqueConstraint` in `__table_args__`).
- [ ] **Step 5: Update `backend/app/models/__init__.py`** to import `PlayerSeasonStat`.
- [ ] **Step 6: Run `pytest backend/tests/test_player_season_stat_model.py -v`** — expect PASS.
- [ ] **Step 7: Generate the migration** — `cd backend && DATABASE_URL=postgresql://football_scout:football_scout@localhost:5432/football_scout alembic revision --autogenerate -m "player season stats"` (with `docker compose up -d postgres` running); rename the generated file to `0002_player_season_stats.py` if needed and confirm it creates `player_season_stats` with the unique constraint.
- [ ] **Step 8: Manual verification** — `alembic upgrade head`, then `docker compose exec -T postgres psql -U football_scout -d football_scout -c '\d player_season_stats'`. Expected: lists all columns from the Interfaces block above.
- [ ] **Step 9: Commit**

```bash
git add backend/app/models/player_season_stat.py backend/app/models/__init__.py backend/alembic/versions/0002_player_season_stats.py backend/tests/test_player_season_stat_model.py
git commit -m "feat: add player_season_stats model and migration"
```

---

### Task 4: Repository + builder orchestration

**Files:**
- Create: `backend/app/repositories/player_season_stat_repository.py`, `backend/app/services/features/player_season_stats_builder.py`
- Test: `backend/tests/test_player_season_stats_builder.py`

**Interfaces:**
- Consumes: `aggregate_season` (Task 1), `compute_percentiles`, `PlayerSeasonPercentiles` (Task 2), `PlayerSeasonStat` (Task 3).
- Produces: `upsert_player_season_stat(session: Session, aggregate: PlayerSeasonAggregate, percentiles: PlayerSeasonPercentiles, season_id: int) -> PlayerSeasonStat` (updates in place if a `(player_id, season_id)` row exists, else inserts); `build_season_features(session: Session, season_id: int) -> int` (returns the number of players processed) — the single entry point the CLI script calls.

- [ ] **Step 1: Write `test_player_season_stats_builder.py::test_build_season_features_creates_expected_rows`** — seed the same fixture as Task 1's `test_aggregate_season_sums_stats_and_computes_per_90` (one season, one player with two matches). Call `build_season_features(session, season_id)`, assert it returns `1`, and assert exactly one `PlayerSeasonStat` row exists with `shots_per_90 == 3.0` and `position_group == "FW"` (percentile `50.0` as the lone cohort member, per Task 2).
- [ ] **Step 2: Write `test_player_season_stats_builder.py::test_build_season_features_is_idempotent`** — call `build_season_features` twice with identical inputs, assert `player_season_stats` row count is unchanged and the row's values are unchanged.
- [ ] **Step 3: Run `pytest backend/tests/test_player_season_stats_builder.py -v`** — expect FAIL.
- [ ] **Step 4: Implement `player_season_stat_repository.py::upsert_player_season_stat`** following `PlayerMatchStat`'s upsert pattern from Task 6 of the StatsBomb plan (`select(...).where(player_id=..., season_id=...).scalar_one_or_none()`, update-in-place or insert).
- [ ] **Step 5: Implement `player_season_stats_builder.py::build_season_features`** — call `aggregate_season(session, season_id)`, call `compute_percentiles(aggregates)`, for each aggregate call `upsert_player_season_stat` with its matching `PlayerSeasonPercentiles` (by `player_id`), return `len(aggregates)`.
- [ ] **Step 6: Run `pytest backend/tests/test_player_season_stats_builder.py -v`** — expect PASS.
- [ ] **Step 7: Commit**

```bash
git add backend/app/repositories/player_season_stat_repository.py backend/app/services/features/player_season_stats_builder.py backend/tests/test_player_season_stats_builder.py
git commit -m "feat: add player season stats repository and build orchestration"
```

---

### Task 5: CLI script

**Files:**
- Create: `scripts/features/build_player_features.py`
- Test: `backend/tests/test_build_player_features_cli.py`

**Interfaces:**
- Consumes: `build_season_features` (Task 4), `SessionLocal` (existing `app.core.db`).
- Produces: `if __name__ == "__main__":` CLI with `argparse` flag `--season-id` (required, `int`); prints `f"Processed {count} players for season {season_id}"` and commits.

- [ ] **Step 1: Write `test_build_player_features_cli.py::test_main_commits_and_prints_summary`** — monkeypatch `build_season_features` to a stub returning `3`, invoke the script's `main(["--season-id", "106"])` function, capture stdout, assert it contains `"3"` and `"106"`, and assert the session's `commit` was called (via a spy/fake `SessionLocal`).
- [ ] **Step 2: Run `pytest backend/tests/test_build_player_features_cli.py -v`** — expect FAIL (module doesn't exist).
- [ ] **Step 3: Implement `build_player_features.py`** — a `main(argv: list[str] | None = None) -> None` function parsing `--season-id` with `argparse`, opening a `SessionLocal()` session, calling `build_season_features(session, season_id)` inside a `try`/`except` that rolls back and re-raises on failure, committing and printing the summary on success; `if __name__ == "__main__": main()`.
- [ ] **Step 4: Run `pytest backend/tests/test_build_player_features_cli.py -v`** — expect PASS.
- [ ] **Step 5: Manual verification (real Postgres, real ingested World Cup 2022 data)** — `docker compose up -d postgres`, ensure season 106 was already ingested (Task 7 of the StatsBomb plan), then `cd backend && DATABASE_URL=postgresql://football_scout:football_scout@localhost:5432/football_scout python ../scripts/features/build_player_features.py --season-id <internal season id>`. Expected: prints a nonzero player count, and `docker compose exec -T postgres psql -U football_scout -d football_scout -c 'SELECT position_group, shots_per_90, shots_per_90_percentile FROM player_season_stats ORDER BY shots_per_90_percentile DESC LIMIT 5;'` returns plausible rows (top scorers' percentiles near 100).
- [ ] **Step 6: Run the full backend test suite**: `cd backend && .venv/bin/python -m pytest -v` — expect all PASS.
- [ ] **Step 7: Commit**

```bash
git add scripts/features/build_player_features.py backend/tests/test_build_player_features_cli.py
git commit -m "feat: add CLI script to build per-season player features"
```

---

## Phase Boundary

This plan stops once `player_season_stats` can be built from already-ingested StatsBomb data and queried directly in the database, with per-90 metrics and within-cohort percentiles for every player with at least one match appearance. The next plan (Player Profiles: profile API, statistics API, frontend charts — guide Phase 5) reads from `player_season_stats` rather than extending it, and should be written after this one is merged and verified end-to-end. Position-specific weighted scoring (guide section 13, Phase 6 — Baseline Scout) and league-strength adjustment across multiple competitions (guide section 14, deferred until a second competition is ingested) are explicitly out of scope here.
