"""Deterministic, non-destructive migration ledger for ELYIO.

Usage from ``backend/``:
  python scripts/migrate.py status
  python scripts/migrate.py baseline
  python scripts/migrate.py apply
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
BASELINE_ID = "0001_production_schema_baseline"
REQUIRED_BASELINE_TABLES = {
    "museums",
    "artworks",
    "artwork_catalog_memberships",
    "product_events",
    "admin_sessions",
    "admin_login_attempts",
}


@dataclass(frozen=True)
class Migration:
    migration_id: str
    path: Path
    checksum: str
    sql: str


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    rows = []
    for path in sorted(directory.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        sql = path.read_text(encoding="utf-8")
        rows.append(Migration(path.stem, path, hashlib.sha256(sql.encode("utf-8")).hexdigest(), sql))
    ids = [row.migration_id for row in rows]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise RuntimeError("migration IDs must be unique and lexically ordered")
    return rows


def ensure_ledger(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id VARCHAR PRIMARY KEY,
                checksum VARCHAR NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL,
                duration_ms INTEGER NOT NULL
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migration_attempts (
                id VARCHAR PRIMARY KEY,
                migration_id VARCHAR NOT NULL,
                checksum VARCHAR NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                finished_at TIMESTAMPTZ,
                status VARCHAR NOT NULL,
                error TEXT
            )
        """))


def applied_migrations(engine) -> dict[str, str]:
    ensure_ledger(engine)
    with engine.connect() as connection:
        return dict(connection.execute(text("SELECT migration_id, checksum FROM schema_migrations ORDER BY migration_id")).all())


def baseline(engine, migrations: list[Migration]) -> None:
    ensure_ledger(engine)
    existing = set(inspect(engine).get_table_names())
    missing = sorted(REQUIRED_BASELINE_TABLES - existing)
    if missing:
        raise RuntimeError(f"cannot baseline: required production tables missing: {', '.join(missing)}")
    baseline_migration = next((row for row in migrations if row.migration_id == BASELINE_ID), None)
    if baseline_migration is None:
        raise RuntimeError(f"baseline migration {BASELINE_ID!r} is missing")
    applied = applied_migrations(engine)
    if BASELINE_ID in applied:
        if applied[BASELINE_ID] != baseline_migration.checksum:
            raise RuntimeError("baseline checksum differs from the applied ledger")
        return
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO schema_migrations (migration_id, checksum, applied_at, duration_ms) VALUES (:id, :checksum, :now, 0)"),
            {"id": BASELINE_ID, "checksum": baseline_migration.checksum, "now": now},
        )


def apply_pending(engine, migrations: list[Migration]) -> list[str]:
    applied = applied_migrations(engine)
    if BASELINE_ID not in applied:
        raise RuntimeError("database is not baselined; run `migrate.py baseline` after reviewing the schema")
    completed = []
    for migration in migrations:
        if migration.migration_id in applied:
            if applied[migration.migration_id] != migration.checksum:
                raise RuntimeError(f"applied migration was modified: {migration.migration_id}")
            continue
        started = datetime.now(timezone.utc)
        attempt_id = str(uuid.uuid4())
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO schema_migration_attempts (id, migration_id, checksum, started_at, status) VALUES (:attempt, :id, :checksum, :started, 'RUNNING')"),
                {"attempt": attempt_id, "id": migration.migration_id, "checksum": migration.checksum, "started": started},
            )
        tick = time.perf_counter()
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql(migration.sql)
                duration_ms = round((time.perf_counter() - tick) * 1000)
                connection.execute(
                    text("INSERT INTO schema_migrations (migration_id, checksum, applied_at, duration_ms) VALUES (:id, :checksum, :now, :duration)"),
                    {"id": migration.migration_id, "checksum": migration.checksum, "now": datetime.now(timezone.utc), "duration": duration_ms},
                )
            with engine.begin() as connection:
                connection.execute(text("UPDATE schema_migration_attempts SET status='APPLIED', finished_at=:now WHERE id=:id"), {"now": datetime.now(timezone.utc), "id": attempt_id})
            completed.append(migration.migration_id)
        except Exception as exc:
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE schema_migration_attempts SET status='FAILED', finished_at=:now, error=:error WHERE id=:id"),
                    {"now": datetime.now(timezone.utc), "error": str(exc)[:4000], "id": attempt_id},
                )
            raise
    return completed


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    parser = argparse.ArgumentParser(description="ELYIO deterministic database migration ledger")
    parser.add_argument("command", choices=("status", "baseline", "apply"))
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL is required")
    engine = create_engine(database_url, pool_pre_ping=True)
    migrations = discover_migrations()
    if args.command == "baseline":
        baseline(engine, migrations)
    elif args.command == "apply":
        for migration_id in apply_pending(engine, migrations):
            print(f"APPLIED {migration_id}")
    applied = applied_migrations(engine)
    for migration in migrations:
        print(f"{'APPLIED' if migration.migration_id in applied else 'PENDING'} {migration.migration_id} {migration.checksum[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
