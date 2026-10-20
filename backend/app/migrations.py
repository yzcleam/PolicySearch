"""Lightweight schema versioning.

The application currently creates its tables through SQLAlchemy metadata and
records the resulting schema version in ``app_meta``.  Future releases can add
an entry to ``MIGRATIONS`` (version -> callable) and the deploy script will
apply it exactly once.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from . import models  # noqa: F401  (register ORM metadata)
from .database import Base

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

MIGRATIONS: dict[int, Callable[[Connection], None]] = {
    # Example for a future release:
    # 2: _migrate_v2_add_document_columns,
}


def _ensure_meta_table(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key VARCHAR(64) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )


def _current_version(conn: Connection) -> int:
    value = conn.execute(
        text("SELECT value FROM app_meta WHERE key = 'schema_version'")
    ).scalar_one_or_none()
    return int(value) if value is not None else 0


def _set_version(conn: Connection, version: int) -> None:
    conn.execute(
        text(
            """
            INSERT INTO app_meta (key, value, updated_at)
            VALUES ('schema_version', :value, now())
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value, updated_at = now()
            """
        ),
        {"value": str(version)},
    )


def run_migrations(engine: Engine) -> int:
    """Create missing tables and apply pending schema migrations."""

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        _ensure_meta_table(conn)
        current = _current_version(conn)

        if current > SCHEMA_VERSION:
            raise RuntimeError(
                f"数据库 schema 版本 {current} 高于当前程序支持的 {SCHEMA_VERSION}，"
                "请升级代码后再启动。"
            )

        for version in sorted(MIGRATIONS):
            if version > current:
                log.info("应用数据库迁移 v%s", version)
                MIGRATIONS[version](conn)
                _set_version(conn, version)
                current = version

        if current == 0:
            _set_version(conn, SCHEMA_VERSION)
            current = SCHEMA_VERSION

        log.info("数据库 schema 版本: v%s", current)
        return current
