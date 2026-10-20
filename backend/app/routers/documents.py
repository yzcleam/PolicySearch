from fastapi import APIRouter, HTTPException

from ..schemas import DocumentOut
from ..services import catalog

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str) -> DocumentOut:
    doc = catalog.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return DocumentOut.model_validate(doc)
