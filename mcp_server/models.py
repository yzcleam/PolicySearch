from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchMode = Literal["smart", "keyword", "exact", "fuzzy"]
SortMode = Literal["relevance", "date_desc", "date_asc"]


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuers: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="发布机关，例如：国务院、国家税务总局。",
    )
    categories: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="政策类型，例如：税收优惠、科技创新。",
    )
    regions: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="适用地区，例如：全国、广东省、深圳市。",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="主题标签，例如：减税降费、专精特新。",
    )
    date_from: date | None = Field(
        default=None,
        description="发布日期下界，ISO 8601 日期，例如 2020-01-01。",
    )
    date_to: date | None = Field(
        default=None,
        description="发布日期上界，ISO 8601 日期，例如 2024-12-31。",
    )


class Highlight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal["title", "summary", "content"]
    text: str


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    title: str
    doc_number: str
    issuer: str
    region: str
    category: str
    tags: list[str]
    issue_date: date | None
    effective_date: date | None
    summary: str
    source_url: str
    status: str
    score: float | None
    highlights: list[Highlight]


class FacetBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    count: int = Field(ge=1)


class Facets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuers: list[FacetBucket]
    categories: list[FacetBucket]
    regions: list[FacetBucket]
    tags: list[FacetBucket]


class SearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=50)
    took_ms: int = Field(ge=0)
    mode: SearchMode
    query: str
    has_more: bool
    next_page: int | None = Field(ge=2)
    hits: list[SearchHit]
    facets: Facets


class PolicyDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    title: str
    doc_number: str
    issuer: str
    region: str
    category: str
    tags: list[str]
    issue_date: date | None
    effective_date: date | None
    summary: str
    source_url: str
    status: str
    content: str
    file_hash: str
    created_at: datetime | None


class GetDocumentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: PolicyDocument


class StatsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: int = Field(ge=0)
    index_docs: int = Field(ge=0)
    index_size_bytes: int = Field(ge=0)
    analyzer: str
    engine: str
    status: str
