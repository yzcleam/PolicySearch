from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from ..database import SessionLocal
from ..models import Document

_UPDATE_COLUMNS = (
    "title",
    "doc_number",
    "issuer",
    "region",
    "category",
    "tags",
    "issue_date",
    "effective_date",
    "content",
    "summary",
    "source_url",
    "file_hash",
    "status",
    "law_db_name",
    "detail_url",
    "province",
    "city",
    "county",
    "category_1",
    "category_2",
    "law_type",
    "pub_depart",
    "pub_num",
    "pub_date",
    "use_date",
    "is_time",
    "detail_flag",
    "detail_html",
    "detail_md",
    "add_time",
)


def _row(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": doc["doc_id"],
        "title": doc.get("title", ""),
        "doc_number": doc.get("doc_number", ""),
        "issuer": doc.get("issuer", ""),
        "region": doc.get("region", ""),
        "category": doc.get("category", ""),
        "tags": doc.get("tags") or [],
        "issue_date": doc.get("issue_date"),
        "effective_date": doc.get("effective_date"),
        "content": doc.get("content", ""),
        "summary": doc.get("summary", ""),
        "source_url": doc.get("source_url", ""),
        "file_hash": doc.get("file_hash", ""),
        "status": doc.get("status", "active"),
        "law_db_name": doc.get("law_db_name", ""),
        "detail_url": doc.get("detail_url", ""),
        "province": doc.get("province", ""),
        "city": doc.get("city", ""),
        "county": doc.get("county", ""),
        "category_1": doc.get("category_1", ""),
        "category_2": doc.get("category_2", ""),
        "law_type": doc.get("law_type", ""),
        "pub_depart": doc.get("pub_depart", ""),
        "pub_num": doc.get("pub_num", ""),
        "pub_date": doc.get("pub_date"),
        "use_date": doc.get("use_date"),
        "is_time": doc.get("is_time", ""),
        "detail_flag": doc.get("detail_flag", ""),
        "detail_html": doc.get("detail_html", ""),
        "detail_md": doc.get("detail_md", ""),
        "add_time": doc.get("add_time", ""),
    }


def upsert_documents(docs: list[dict[str, Any]]) -> int:
    if not docs:
        return 0

    rows = [_row(doc) for doc in docs]
    stmt = insert(Document).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Document.doc_id],
        set_={column: getattr(stmt.excluded, column) for column in _UPDATE_COLUMNS}
        | {"updated_at": func.now()},
    )

    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()
    return len(rows)


def clear_all() -> None:
    with SessionLocal() as session:
        session.execute(delete(Document))
        session.commit()


def get_document(doc_id: str) -> Document | None:
    with SessionLocal() as session:
        return session.execute(
            select(Document).where(Document.doc_id == doc_id)
        ).scalar_one_or_none()


def all_sources() -> list[dict[str, Any]]:
    from .index_service import to_source

    with SessionLocal() as session:
        docs = session.execute(select(Document)).scalars().all()
        return [to_source(doc) for doc in docs]


def stats() -> dict[str, int]:
    with SessionLocal() as session:
        total = session.execute(select(func.count(Document.doc_id))).scalar_one()
    return {"documents": int(total)}
