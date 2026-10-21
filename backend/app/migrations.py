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

SCHEMA_VERSION = 4


def _migrate_v2_api_tokens(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS api_tokens (
                jti VARCHAR(64) PRIMARY KEY,
                name VARCHAR(128) NOT NULL,
                scopes JSON NOT NULL DEFAULT '[]'::json,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                expires_at TIMESTAMP NULL,
                revoked_at TIMESTAMP NULL,
                last_used_at TIMESTAMP NULL
            )
            """
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_api_tokens_name ON api_tokens (name)"
        )
    )


def _migrate_v3_import_jobs(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS import_jobs (
                id VARCHAR(36) PRIMARY KEY,
                source_path VARCHAR(1024) NOT NULL,
                format VARCHAR(16) NOT NULL DEFAULT 'auto',
                status VARCHAR(32) NOT NULL DEFAULT 'queued',
                batch_size INTEGER NOT NULL DEFAULT 500,
                record_limit INTEGER NOT NULL DEFAULT 0,
                index_enabled BOOLEAN NOT NULL DEFAULT true,
                reset BOOLEAN NOT NULL DEFAULT false,
                processed INTEGER NOT NULL DEFAULT 0,
                imported INTEGER NOT NULL DEFAULT 0,
                indexed INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                errors JSON NOT NULL DEFAULT '[]'::json,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                started_at TIMESTAMP NULL,
                finished_at TIMESTAMP NULL
            )
            """
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_import_jobs_status "
            "ON import_jobs (status)"
        )
    )


def _migrate_v4_policy_fields(conn: Connection) -> None:
    columns = {
        "law_db_name": "VARCHAR(64) NOT NULL DEFAULT ''",
        "detail_url": "VARCHAR(512) NOT NULL DEFAULT ''",
        "province": "VARCHAR(512) NOT NULL DEFAULT ''",
        "city": "VARCHAR(64) NOT NULL DEFAULT ''",
        "county": "VARCHAR(64) NOT NULL DEFAULT ''",
        "category_1": "TEXT NOT NULL DEFAULT ''",
        "category_2": "TEXT NOT NULL DEFAULT ''",
        "law_type": "VARCHAR(128) NOT NULL DEFAULT ''",
        "pub_depart": "TEXT NOT NULL DEFAULT ''",
        "pub_num": "VARCHAR(300) NOT NULL DEFAULT ''",
        "pub_date": "DATE NULL",
        "use_date": "DATE NULL",
        "is_time": "VARCHAR(64) NOT NULL DEFAULT ''",
        "detail_flag": "TEXT NOT NULL DEFAULT ''",
        "detail_html": "TEXT NOT NULL DEFAULT ''",
        "detail_md": "TEXT NOT NULL DEFAULT ''",
        "add_time": "VARCHAR(64) NOT NULL DEFAULT ''",
    }
    for column, definition in columns.items():
        conn.execute(
            text(f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {column} {definition}")
        )

    conn.execute(
        text(
            """
            UPDATE documents SET
                law_db_name = CASE WHEN law_db_name = '' THEN 'sample' ELSE law_db_name END,
                detail_url = CASE WHEN detail_url = '' THEN source_url ELSE detail_url END,
                province = CASE WHEN province = '' THEN region ELSE province END,
                category_1 = CASE WHEN category_1 = '' THEN category ELSE category_1 END,
                law_type = CASE WHEN law_type = '' THEN category ELSE law_type END,
                pub_depart = CASE WHEN pub_depart = '' THEN issuer ELSE pub_depart END,
                pub_num = CASE WHEN pub_num = '' THEN doc_number ELSE pub_num END,
                pub_date = COALESCE(pub_date, issue_date),
                use_date = COALESCE(use_date, effective_date),
                is_time = CASE
                    WHEN is_time <> '' THEN is_time
                    WHEN status = 'active' THEN '现行有效'
                    WHEN status = 'inactive' THEN '已失效'
                    ELSE status
                END,
                detail_flag = CASE WHEN detail_flag = '' THEN content ELSE detail_flag END,
                detail_md = CASE WHEN detail_md = '' THEN content ELSE detail_md END,
                add_time = CASE WHEN add_time = '' THEN created_at::text ELSE add_time END
            """
        )
    )
    for column in (
        "law_db_name",
        "province",
        "city",
        "county",
        "law_type",
        "pub_date",
        "use_date",
        "is_time",
    ):
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_documents_{column} "
                f"ON documents ({column})"
            )
        )


MIGRATIONS: dict[int, Callable[[Connection], None]] = {
    2: _migrate_v2_api_tokens,
    3: _migrate_v3_import_jobs,
    4: _migrate_v4_policy_fields,
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
