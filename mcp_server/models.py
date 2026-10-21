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
    law_db_names: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="法规库名称，例如 lar。",
    )
    provinces: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="省级地区，例如 北京市、广东省。",
    )
    cities: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="城市，例如 深圳市。",
    )
    counties: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="区县。",
    )
    category_1: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="一级分类，例如 科技创新。",
    )
    category_2: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="二级分类，例如 专精特新。",
    )
    law_types: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="法规类型，例如 地方性法规、行政法规。",
    )
    pub_departments: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="发布机关，对应源字段 pub_depart。",
    )
    pub_nums: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="文号，对应源字段 pub_num。",
    )
    time_statuses: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="时效性，例如 现行有效、已失效。",
    )
    pub_date_from: date | None = Field(
        default=None,
        description="发布日期下界，对应源字段 pub_date。",
    )
    pub_date_to: date | None = Field(
        default=None,
        description="发布日期上界，对应源字段 pub_date。",
    )
    use_date_from: date | None = Field(
        default=None,
        description="实施日期下界，对应源字段 use_date。",
    )
    use_date_to: date | None = Field(
        default=None,
        description="实施日期上界，对应源字段 use_date。",
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
    law_db_name: str
    detail_url: str
    province: str
    city: str
    county: str
    category_1: str
    category_2: str
    law_type: str
    pub_depart: str
    pub_num: str
    pub_date: date | None
    use_date: date | None
    is_time: str
    add_time: str
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
    law_db_names: list[FacetBucket]
    provinces: list[FacetBucket]
    cities: list[FacetBucket]
    counties: list[FacetBucket]
    category_1: list[FacetBucket]
    category_2: list[FacetBucket]
    law_types: list[FacetBucket]
    pub_departments: list[FacetBucket]
    time_statuses: list[FacetBucket]


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
    law_db_name: str
    detail_url: str
    province: str
    city: str
    county: str
    category_1: str
    category_2: str
    law_type: str
    pub_depart: str
    pub_num: str
    pub_date: date | None
    use_date: date | None
    is_time: str
    detail_flag: str
    detail_html: str
    detail_md: str
    add_time: str


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
