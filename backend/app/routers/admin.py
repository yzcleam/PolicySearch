from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin, require_api_access
from ..models import Document
from ..schemas import AdminResult, SeedRequest, StatsResponse
from ..services import catalog
from ..services.index_service import index_service, to_source
from ..services.sample_data import generate_documents

router = APIRouter(prefix="/api", tags=["admin"])


@router.get(
    "/stats",
    response_model=StatsResponse,
    dependencies=[Depends(require_api_access)],
)
def stats() -> StatsResponse:
    pg = catalog.stats()
    os_stats = index_service.stats()
    online = index_service.ping()
    return StatsResponse(
        documents=pg["documents"],
        index_docs=os_stats["docs"],
        index_size_bytes=os_stats["size_bytes"],
        analyzer=index_service.analyzer_mode() if online else "unknown",
        engine="postgresql + opensearch",
        status="ready" if online else "degraded",
    )


@router.post("/admin/seed", response_model=AdminResult, dependencies=[Depends(require_admin)])
def seed(req: SeedRequest) -> AdminResult:
    try:
        if req.reset:
            catalog.clear_all()
            index_service.delete_all()

        docs = generate_documents(req.count)
        imported = catalog.upsert_documents(docs)

        sources = [to_source(Document(**doc)) for doc in docs]
        indexed = index_service.index_documents(sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导入失败: {exc}") from exc

    return AdminResult(
        message=f"已导入 {imported} 份示例文档，索引 {indexed} 条",
        documents=catalog.stats()["documents"],
        indexed=indexed,
        analyzer=index_service.analyzer_mode(),
    )


@router.post("/admin/reindex", response_model=AdminResult, dependencies=[Depends(require_admin)])
def reindex() -> AdminResult:
    index_service.ensure_index(force=True)
    sources = catalog.all_sources()
    indexed = index_service.index_documents(sources)
    return AdminResult(
        message=f"索引重建完成，共 {indexed} 条",
        documents=catalog.stats()["documents"],
        indexed=indexed,
        analyzer=index_service.analyzer_mode(),
    )


@router.post("/admin/clear", response_model=AdminResult, dependencies=[Depends(require_admin)])
def clear() -> AdminResult:
    catalog.clear_all()
    index_service.delete_all()
    return AdminResult(message="已清空全部文档与索引", analyzer=index_service.analyzer_mode())
