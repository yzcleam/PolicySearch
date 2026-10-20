from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_api_access
from ..schemas import SearchRequest, SearchResponse
from ..services import search_service

router = APIRouter(prefix="/api", tags=["search"], dependencies=[Depends(require_api_access)])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    try:
        return search_service.search(req)
    except Exception as exc:  # pragma: no cover - surfaced to the UI
        raise HTTPException(status_code=500, detail=f"检索失败: {exc}") from exc
