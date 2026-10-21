from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from ..database import SessionLocal
from ..models import ImportJob
from . import importer


def create_job(
    *,
    source_path: str,
    fmt: str,
    batch_size: int,
    limit: int,
    index: bool,
    reset: bool,
) -> ImportJob:
    job = ImportJob(
        id=uuid4().hex,
        source_path=source_path,
        format=fmt,
        status="queued",
        batch_size=batch_size,
        record_limit=limit,
        index_enabled=index,
        reset=reset,
        message="等待开始",
    )
    with SessionLocal() as session:
        session.add(job)
        session.commit()
        session.refresh(job)
    return job


def get_job(job_id: str) -> ImportJob | None:
    with SessionLocal() as session:
        return session.get(ImportJob, job_id)


def list_jobs(limit: int = 20) -> list[ImportJob]:
    with SessionLocal() as session:
        return list(
            session.query(ImportJob)
            .order_by(ImportJob.created_at.desc())
            .limit(limit)
            .all()
        )


def _update(job_id: str, **values: Any) -> None:
    with SessionLocal() as session:
        job = session.get(ImportJob, job_id)
        if job is None:
            return
        for key, value in values.items():
            setattr(job, key, value)
        session.commit()


def run_import_job(
    job_id: str,
    *,
    source_path: str,
    fmt: str,
    batch_size: int,
    limit: int,
    index: bool,
    reset: bool,
    zip_password: str | None,
    sheet: str | None,
) -> None:
    _update(
        job_id,
        status="running",
        started_at=datetime.utcnow(),
        message="正在读取文件",
    )

    def progress(result: importer.ImportResult) -> None:
        _update(
            job_id,
            processed=result.total,
            imported=result.imported,
            indexed=result.indexed,
            skipped=result.skipped,
            failed=result.failed,
            message=result.message,
        )

    try:
        result = importer.import_source(
            source_path,
            fmt=fmt,
            batch_size=batch_size,
            limit=limit,
            index=index,
            reset=reset,
            zip_password=zip_password,
            sheet=sheet,
            progress=progress,
        )
        _update(
            job_id,
            status="completed",
            processed=result.total,
            imported=result.imported,
            indexed=result.indexed,
            skipped=result.skipped,
            failed=result.failed,
            errors=result.errors,
            message=result.message,
            finished_at=datetime.utcnow(),
        )
    except Exception as exc:
        _update(
            job_id,
            status="failed",
            message=f"{type(exc).__name__}: {exc}",
            errors=[str(exc)][:20],
            finished_at=datetime.utcnow(),
        )
