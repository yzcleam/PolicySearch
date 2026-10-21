"""Query construction and result shaping for the four search modes."""

from __future__ import annotations

import logging
from typing import Any

from opensearchpy.exceptions import TransportError

from ..schemas import (
    FacetBucket,
    HighlightFragment,
    SearchFilters,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from .index_service import index_service

log = logging.getLogger(__name__)

TEXT_FIELDS = ["title^4", "summary^2", "content"]

_FACET_FIELDS = {
    "issuers": "issuer",
    "categories": "category",
    "regions": "region",
    "tags": "tags",
    "law_db_names": "law_db_name",
    "provinces": "province",
    "cities": "city",
    "counties": "county",
    "category_1": "category_1",
    "category_2": "category_2",
    "law_types": "law_type",
    "pub_departments": "pub_depart",
    "time_statuses": "is_time",
}


def _filter_clauses(filters: SearchFilters) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []

    if filters.issuers:
        clauses.append({"terms": {"issuer": filters.issuers}})
    if filters.categories:
        clauses.append({"terms": {"category": filters.categories}})
    if filters.regions:
        clauses.append({"terms": {"region": filters.regions}})
    if filters.tags:
        clauses.append({"terms": {"tags": filters.tags}})
    if filters.law_db_names:
        clauses.append({"terms": {"law_db_name": filters.law_db_names}})
    if filters.provinces:
        clauses.append({"terms": {"province": filters.provinces}})
    if filters.cities:
        clauses.append({"terms": {"city": filters.cities}})
    if filters.counties:
        clauses.append({"terms": {"county": filters.counties}})
    if filters.category_1:
        clauses.append({"terms": {"category_1": filters.category_1}})
    if filters.category_2:
        clauses.append({"terms": {"category_2": filters.category_2}})
    if filters.law_types:
        clauses.append({"terms": {"law_type": filters.law_types}})
    if filters.pub_departments:
        clauses.append({"terms": {"pub_depart": filters.pub_departments}})
    if filters.pub_nums:
        clauses.append({"terms": {"pub_num": filters.pub_nums}})
    if filters.time_statuses:
        clauses.append({"terms": {"is_time": filters.time_statuses}})

    date_range: dict[str, str] = {}
    if filters.date_from:
        date_range["gte"] = filters.date_from.isoformat()
    if filters.date_to:
        date_range["lte"] = filters.date_to.isoformat()
    if date_range:
        clauses.append({"range": {"issue_date": date_range}})

    pub_range: dict[str, str] = {}
    if filters.pub_date_from:
        pub_range["gte"] = filters.pub_date_from.isoformat()
    if filters.pub_date_to:
        pub_range["lte"] = filters.pub_date_to.isoformat()
    if pub_range:
        clauses.append({"range": {"pub_date": pub_range}})

    use_range: dict[str, str] = {}
    if filters.use_date_from:
        use_range["gte"] = filters.use_date_from.isoformat()
    if filters.use_date_to:
        use_range["lte"] = filters.use_date_to.isoformat()
    if use_range:
        clauses.append({"range": {"use_date": use_range}})

    return clauses


def _core_query(req: SearchRequest) -> dict[str, Any]:
    query = req.query.strip()

    if not query:
        return {"match_all": {}}

    if req.mode == "exact":
        return {
            "bool": {
                "should": [
                    {
                        "match_phrase": {
                            "title": {"query": query, "slop": req.slop, "boost": 4}
                        }
                    },
                    {
                        "match_phrase": {
                            "summary": {"query": query, "slop": req.slop, "boost": 2}
                        }
                    },
                    {
                        "match_phrase": {
                            "content": {"query": query, "slop": req.slop}
                        }
                    },
                ],
                "minimum_should_match": 1,
            }
        }

    if req.mode == "fuzzy":
        return {
            "multi_match": {
                "query": query,
                "fields": TEXT_FIELDS,
                "type": "best_fields",
                "fuzziness": "AUTO",
                "prefix_length": 1,
                "max_expansions": 50,
            }
        }

    if req.mode == "smart":
        return {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": TEXT_FIELDS,
                            "type": "best_fields",
                            "operator": "and",
                            "boost": 2,
                        }
                    },
                    {
                        "match_phrase": {
                            "content": {"query": query, "slop": req.slop, "boost": 3}
                        }
                    },
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "summary^2", "content"],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                            "prefix_length": 1,
                            "boost": 1,
                        }
                    },
                ],
                "minimum_should_match": 1,
            }
        }

    # default: keyword / BM25
    return {
        "multi_match": {
            "query": query,
            "fields": TEXT_FIELDS,
            "type": "best_fields",
            "operator": "or",
        }
    }


def _sort_clause(req: SearchRequest) -> list[Any]:
    if req.sort == "date_desc":
        return [
            {"pub_date": {"order": "desc", "missing": "_last"}},
            {"issue_date": {"order": "desc", "missing": "_last"}},
            "_score",
        ]
    if req.sort == "date_asc":
        return [
            {"pub_date": {"order": "asc", "missing": "_last"}},
            {"issue_date": {"order": "asc", "missing": "_last"}},
            "_score",
        ]
    if not req.query.strip():
        return [
            {"pub_date": {"order": "desc", "missing": "_last"}},
            {"issue_date": {"order": "desc", "missing": "_last"}},
        ]
    return [
        "_score",
        {"pub_date": {"order": "desc", "missing": "_last"}},
        {"issue_date": {"order": "desc", "missing": "_last"}},
    ]


def _highlight_clause(enabled: bool) -> dict[str, Any] | None:
    if not enabled:
        return None
    return {
        "pre_tags": ["<mark>"],
        "post_tags": ["</mark>"],
        "fragment_size": 180,
        "number_of_fragments": 3,
        "fields": {
            "title": {"number_of_fragments": 0},
            "summary": {"number_of_fragments": 2, "fragment_size": 160},
            "content": {"number_of_fragments": 3, "fragment_size": 180},
        },
    }


def _parse_facets(aggregations: dict[str, Any]) -> dict[str, list[FacetBucket]]:
    result: dict[str, list[FacetBucket]] = {}
    for name in _FACET_FIELDS:
        buckets = aggregations.get(name, {}).get("buckets", [])
        result[name] = [
            FacetBucket(value=str(b.get("key", "")), count=int(b.get("doc_count", 0)))
            for b in buckets
        ]
    return result


def _parse_hit(raw: dict[str, Any]) -> SearchHit:
    source = raw.get("_source", {})
    highlights = raw.get("highlight", {})
    fragments: list[HighlightFragment] = []
    for field in ("title", "summary", "content"):
        for text in highlights.get(field, [])[:3]:
            fragments.append(HighlightFragment(field=field, text=text))

    return SearchHit(
        doc_id=source.get("doc_id", raw.get("_id", "")),
        title=source.get("title", ""),
        doc_number=source.get("doc_number", ""),
        issuer=source.get("issuer", ""),
        region=source.get("region", ""),
        category=source.get("category", ""),
        tags=list(source.get("tags") or []),
        issue_date=source.get("issue_date"),
        effective_date=source.get("effective_date"),
        summary=source.get("summary", ""),
        source_url=source.get("source_url", ""),
        status=source.get("status", "active"),
        law_db_name=source.get("law_db_name", ""),
        detail_url=source.get("detail_url", ""),
        province=source.get("province", ""),
        city=source.get("city", ""),
        county=source.get("county", ""),
        category_1=source.get("category_1", ""),
        category_2=source.get("category_2", ""),
        law_type=source.get("law_type", ""),
        pub_depart=source.get("pub_depart", ""),
        pub_num=source.get("pub_num", ""),
        pub_date=source.get("pub_date"),
        use_date=source.get("use_date"),
        is_time=source.get("is_time", ""),
        add_time=source.get("add_time", ""),
        score=raw.get("_score"),
        highlights=fragments,
    )


def search(req: SearchRequest, highlight: bool = True) -> SearchResponse:
    body: dict[str, Any] = {
        "query": {
            "bool": {
                "must": [_core_query(req)],
                "filter": _filter_clauses(req.filters),
            }
        },
        "from": (req.page - 1) * req.size,
        "size": req.size,
        "sort": _sort_clause(req),
        "track_total_hits": True,
        "aggs": {
            name: {"terms": {"field": field, "size": 40}}
            for name, field in _FACET_FIELDS.items()
        },
    }

    highlight_clause = _highlight_clause(highlight)
    if highlight_clause:
        body["highlight"] = highlight_clause

    try:
        raw = index_service.client.search(index=index_service.index, body=body)
    except TransportError as exc:
        raise RuntimeError(f"OpenSearch 查询失败: {exc}") from exc

    total = raw.get("hits", {}).get("total", {})
    total_value = total.get("value", 0) if isinstance(total, dict) else int(total)

    return SearchResponse(
        total=int(total_value),
        page=req.page,
        size=req.size,
        took_ms=int(raw.get("took", 0)),
        mode=req.mode,
        query=req.query,
        hits=[_parse_hit(h) for h in raw.get("hits", {}).get("hits", [])],
        facets=_parse_facets(raw.get("aggregations", {})),
    )
