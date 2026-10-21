from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from ..auth import require_admin
from ..models import ImportJob
from ..schemas import ImportJobList, ImportJobOut, ImportRequest
from ..services import import_jobs

router = APIRouter(
    prefix="/api/admin/import",
    tags=["admin-import"],
    dependencies=[Depends(require_admin)],
)


def _job_out(job: ImportJob) -> ImportJobOut:
    return ImportJobOut(
        id=job.id,
        source_path=job.source_path,
        format=job.format,
        status=job.status,
        batch_size=job.batch_size,
        record_limit=job.record_limit,
        index_enabled=job.index_enabled,
        reset=job.reset,
        processed=job.processed,
        imported=job.imported,
        indexed=job.indexed,
        skipped=job.skipped,
        failed=job.failed,
        message=job.message,
        errors=list(job.errors or []),
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.post("", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
def start_import(
    req: ImportRequest,
    background_tasks: BackgroundTasks,
) -> ImportJobOut:
    source = Path(req.path).expanduser()
    if not source.is_file():
        raise HTTPException(status_code=400, detail=f"文件不存在: {source}")
    if req.format == "excel" and source.suffix.lower() not in {".xlsx", ".xlsm", ".zip"}:
        raise HTTPException(status_code=400, detail="Excel 目前支持 .xlsx / .xlsm")

    job = import_jobs.create_job(
        source_path=str(source.resolve()),
        fmt=req.format,
        batch_size=req.batch_size,
        limit=req.limit,
        index=req.index,
        reset=req.reset,
    )
    background_tasks.add_task(
        import_jobs.run_import_job,
        job.id,
        source_path=str(source.resolve()),
        fmt=req.format,
        batch_size=req.batch_size,
        limit=req.limit,
        index=req.index,
        reset=req.reset,
        zip_password=req.zip_password,
        sheet=req.sheet,
    )
    return _job_out(job)


@router.get("", response_model=ImportJobList)
def list_imports(limit: int = 20) -> ImportJobList:
    limit = max(1, min(limit, 100))
    return ImportJobList(jobs=[_job_out(job) for job in import_jobs.list_jobs(limit)])


@router.get("/{job_id}", response_model=ImportJobOut)
def get_import(job_id: str) -> ImportJobOut:
    job = import_jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return _job_out(job)
