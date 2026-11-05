# Known Gaps

## Critical

### 1. Cron pipeline has no type conversion
The online pipeline (`ingest.py` -> `insert.py`) passes raw CSV strings directly to PostgreSQL and relies on implicit casting. The seed path (`migrate.py`) properly converts values via `convert_value()`.

**Risk:** whitespace strings like `" "` in numeric/date columns will crash the entire 1000-row batch. Any unparseable value takes down the batch with no row-level fallback.

**Fix:** add type conversion in `build_data()` (or before `insert_data_in_database`), similar to `migrate.py:convert_value`. Consider row-by-row fallback on batch failure.

### 2. Batch count calculation is wrong
`db/insert.py:29` — `num_batches = (len(data) + BATCH_SIZE - 1)` is missing `// BATCH_SIZE`. Logged progress shows wrong numbers (e.g. 1999 instead of 2).

Also `batch_num = i` on line 39 shows the row index, not the batch number.

### 3. Hardcoded credentials in source code
- `config.py:7` — database URL default contains `fii:fii123@localhost:5432`
- `docker-compose.yaml:7-8` — `POSTGRES_PASSWORD: fii123`

Defaults should be empty; credentials should only come from `.env` or environment variables.

## Improvements

### 4. `updated_at` column won't auto-update through ORM
`TimestampMixin` uses `server_default=func.now()` which only fires on INSERT. The upsert code in `insert.py` manually sets it (correct), but any future code path that updates rows through SQLAlchemy ORM will leave `updated_at` stale. Add `onupdate=func.now()` to the column definition.

### 5. Module-level engine creation
`model.py:299` — `engine = create_engine(settings.database_url)` runs at import time, coupling database connection to module import. Makes testing harder and forces a connection even when only importing models.

### 6. `match/case` usage in `ingest.py`
Lines 23-39 use structural pattern matching as a glorified `if/elif`. The `case file if file == ...` pattern always matches the variable binding; only the guard does real work. Replace with plain `if/elif` for clarity.

### 7. `psycopg2-binary` in production
The psycopg2 docs recommend the non-binary package (`psycopg2`) for production deployments due to potential OS/SSL compatibility issues with the binary wheels.
