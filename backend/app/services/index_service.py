"""OpenSearch index management.

The index is created with the IK analyzer when the plugin is present and falls
back to the built-in ``cjk`` (bigram) analyzer otherwise, so the stack stays
usable even without the plugin.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import NotFoundError, RequestError, TransportError
from opensearchpy.helpers import bulk

from ..config import get_settings

log = logging.getLogger(__name__)

TEXT_FIELDS = ("title", "summary", "content")

_MAPPING_TEMPLATE: dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "refresh_interval": "1s",
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "doc_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
            },
            "summary": {"type": "text"},
            "content": {"type": "text"},
            "doc_number": {"type": "keyword"},
            "issuer": {"type": "keyword"},
            "region": {"type": "keyword"},
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "issue_date": {
                "type": "date",
                "format": "strict_date_optional_time||yyyy-MM-dd",
            },
            "effective_date": {
                "type": "date",
                "format": "strict_date_optional_time||yyyy-MM-dd",
            },
            "source_url": {"type": "keyword", "index": False},
            "file_hash": {"type": "keyword", "index": False},
            "status": {"type": "keyword"},
            "law_db_name": {"type": "keyword"},
            "detail_url": {"type": "keyword", "index": False},
            "province": {"type": "keyword", "ignore_above": 512},
            "city": {"type": "keyword", "ignore_above": 64},
            "county": {"type": "keyword", "ignore_above": 64},
            "category_1": {"type": "keyword", "ignore_above": 1024},
            "category_2": {"type": "keyword", "ignore_above": 1024},
            "law_type": {"type": "keyword", "ignore_above": 128},
            "pub_depart": {"type": "keyword", "ignore_above": 512},
            "pub_num": {"type": "keyword", "ignore_above": 300},
            "pub_date": {
                "type": "date",
                "format": "strict_date_optional_time||yyyy-MM-dd",
            },
            "use_date": {
                "type": "date",
                "format": "strict_date_optional_time||yyyy-MM-dd",
            },
            "is_time": {"type": "keyword"},
            "detail_md": {"type": "text", "index": False},
            "detail_flag": {"type": "text", "index": False},
            "detail_html": {"type": "text", "index": False},
            "add_time": {"type": "keyword"},
        },
    },
}


def _definition(analyzer: str | None) -> dict[str, Any]:
    import copy

    body = copy.deepcopy(_MAPPING_TEMPLATE)

    if analyzer == "ik":
        body["settings"]["analysis"] = {
            "analyzer": {
                "policy_index": {
                    "type": "custom",
                    "tokenizer": "ik_max_word",
                    "filter": ["lowercase"],
                },
                "policy_search": {
                    "type": "custom",
                    "tokenizer": "ik_smart",
                    "filter": ["lowercase"],
                },
            }
        }
        index_analyzer, search_analyzer = "policy_index", "policy_search"
    else:
        index_analyzer = search_analyzer = "cjk"

    for field in TEXT_FIELDS:
        body["mappings"]["properties"][field]["analyzer"] = index_analyzer
        body["mappings"]["properties"][field]["search_analyzer"] = search_analyzer

    return body


class IndexService:
    def __init__(self) -> None:
        settings = get_settings()
        self.index = settings.opensearch_index
        self.client = OpenSearch(
            hosts=[settings.opensearch_url],
            use_ssl=settings.opensearch_url.startswith("https"),
            verify_certs=False,
            connection_class=RequestsHttpConnection,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
            http_compress=True,
        )

    # ------------------------------------------------------------------ health
    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception:  # pragma: no cover - defensive
            return False

    def ik_available(self) -> bool:
        try:
            self.client.transport.perform_request(
                "POST",
                "/_analyze",
                body={"analyzer": "ik_max_word", "text": "增值税留抵退税"},
            )
            return True
        except Exception:
            return False

    def analyzer_mode(self) -> str:
        return "ik" if self.ik_available() else "cjk"

    # ------------------------------------------------------------------- index
    def ensure_index(self, force: bool = False) -> str:
        exists = False
        try:
            exists = bool(self.client.indices.exists(index=self.index))
        except Exception as exc:
            raise RuntimeError(f"OpenSearch 不可用: {exc}") from exc

        if exists and not force:
            return self.analyzer_mode()

        if exists:
            self.client.indices.delete(index=self.index)

        mode = self.analyzer_mode()
        try:
            self.client.indices.create(index=self.index, body=_definition(mode))
        except RequestError as exc:
            if mode == "ik":
                log.warning("IK 索引创建失败，回退到 cjk 分析器: %s", exc)
                self.client.indices.create(index=self.index, body=_definition("cjk"))
                mode = "cjk"
            else:
                raise
        log.info("OpenSearch 索引 %s 已创建 (analyzer=%s)", self.index, mode)
        return mode

    def count(self) -> int:
        try:
            return int(self.client.count(index=self.index).get("count", 0))
        except (NotFoundError, TransportError):
            return 0

    def stats(self) -> dict[str, Any]:
        try:
            stats = self.client.indices.stats(index=self.index)
            size = stats["_all"]["primaries"]["store"]["size_in_bytes"]
            count = stats["_all"]["primaries"]["docs"]["count"]
            return {"docs": int(count), "size_bytes": int(size)}
        except Exception:
            return {"docs": 0, "size_bytes": 0}

    # ------------------------------------------------------------------- write
    def index_documents(self, docs: Iterable[dict[str, Any]], refresh: bool = True) -> int:
        actions = [
            {"_index": self.index, "_id": doc["doc_id"], "_source": doc}
            for doc in docs
        ]
        if not actions:
            return 0
        success, errors = bulk(
            self.client, actions, refresh=refresh, raise_on_error=False
        )
        if errors:
            log.warning("批量索引出现 %s 条失败记录", len(errors))
        return int(success)

    def delete_all(self) -> None:
        try:
            self.client.delete_by_query(
                index=self.index,
                body={"query": {"match_all": {}}},
                refresh=True,
                conflicts="proceed",
            )
        except NotFoundError:
            pass


def to_source(doc: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy Document into an OpenSearch source document."""

    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "summary": doc.summary or "",
        "content": doc.content or "",
        "doc_number": doc.doc_number or "",
        "issuer": doc.issuer or "",
        "region": doc.region or "",
        "category": doc.category or "",
        "tags": list(doc.tags or []),
        "issue_date": doc.issue_date.isoformat() if doc.issue_date else None,
        "effective_date": doc.effective_date.isoformat()
        if doc.effective_date
        else None,
        "source_url": doc.source_url or "",
        "file_hash": doc.file_hash or "",
        "status": getattr(doc, "status", "active") or "active",
        "law_db_name": getattr(doc, "law_db_name", "") or "",
        "detail_url": getattr(doc, "detail_url", "") or "",
        "province": getattr(doc, "province", "") or "",
        "city": getattr(doc, "city", "") or "",
        "county": getattr(doc, "county", "") or "",
        "category_1": getattr(doc, "category_1", "") or "",
        "category_2": getattr(doc, "category_2", "") or "",
        "law_type": getattr(doc, "law_type", "") or "",
        "pub_depart": getattr(doc, "pub_depart", "") or "",
        "pub_num": getattr(doc, "pub_num", "") or "",
        "pub_date": getattr(doc, "pub_date", None).isoformat()
        if getattr(doc, "pub_date", None)
        else None,
        "use_date": getattr(doc, "use_date", None).isoformat()
        if getattr(doc, "use_date", None)
        else None,
        "is_time": getattr(doc, "is_time", "") or "",
        "detail_md": getattr(doc, "detail_md", "") or "",
        "detail_flag": getattr(doc, "detail_flag", "") or "",
        "detail_html": getattr(doc, "detail_html", "") or "",
        "add_time": getattr(doc, "add_time", "") or "",
    }


index_service = IndexService()
