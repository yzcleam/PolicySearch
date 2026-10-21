from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchMode = Literal["keyword", "exact", "fuzzy", "smart"]
SortMode = Literal["relevance", "date_desc", "date_asc"]


class SearchFilters(BaseModel):
    issuers: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None

    law_db_names: list[str] = Field(default_factory=list)
    provinces: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    counties: list[str] = Field(default_factory=list)
    category_1: list[str] = Field(default_factory=list)
    category_2: list[str] = Field(default_factory=list)
    law_types: list[str] = Field(default_factory=list)
    pub_departments: list[str] = Field(default_factory=list)
    pub_nums: list[str] = Field(default_factory=list)
    time_statuses: list[str] = Field(default_factory=list)
    pub_date_from: date | None = None
    pub_date_to: date | None = None
    use_date_from: date | None = None
    use_date_to: date | None = None


class SearchRequest(BaseModel):
    query: str = ""
    mode: SearchMode = "keyword"
    filters: SearchFilters = Field(default_factory=SearchFilters)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=50)
    sort: SortMode = "relevance"
    slop: int = Field(default=2, ge=0, le=10)


class DocumentBase(BaseModel):
    doc_id: str
    title: str
    doc_number: str = ""
    issuer: str = ""
    region: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    issue_date: date | None = None
    effective_date: date | None = None
    summary: str = ""
    source_url: str = ""
    status: str = "active"
    law_db_name: str = ""
    detail_url: str = ""
    province: str = ""
    city: str = ""
    county: str = ""
    category_1: str = ""
    category_2: str = ""
    law_type: str = ""
    pub_depart: str = ""
    pub_num: str = ""
    pub_date: date | None = None
    use_date: date | None = None
    is_time: str = ""
    add_time: str = ""


class DocumentOut(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    content: str = ""
    detail_md: str = ""
    detail_flag: str = ""
    detail_html: str = ""
    file_hash: str = ""
    created_at: datetime | None = None


class HighlightFragment(BaseModel):
    field: str
    text: str


class SearchHit(DocumentBase):
    score: float | None = None
    highlights: list[HighlightFragment] = Field(default_factory=list)


class FacetBucket(BaseModel):
    value: str
    count: int


class SearchResponse(BaseModel):
    total: int
    page: int
    size: int
    took_ms: int
    mode: SearchMode
    query: str
    hits: list[SearchHit]
    facets: dict[str, list[FacetBucket]] = Field(default_factory=dict)


class SeedRequest(BaseModel):
    count: int = Field(default=320, ge=1, le=5000)
    reset: bool = False


class AdminResult(BaseModel):
    message: str
    documents: int = 0
    indexed: int = 0
    analyzer: str = ""


class StatsResponse(BaseModel):
    documents: int
    index_docs: int
    index_size_bytes: int
    analyzer: str
    engine: str
    status: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str = "admin"


class AdminMe(BaseModel):
    username: str
    role: str
    scopes: list[str]
    expires_at: int | None = None


class VerifyTokenResponse(BaseModel):
    valid: bool = True
    subject: str
    role: str
    scopes: list[str]
    token_type: str
    expires_at: int | None = None
    jti: str | None = None


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=lambda: ["policy:read"], max_length=10)
    expires_in_days: int = Field(default=90, ge=1, le=3650)


class ApiTokenInfo(BaseModel):
    jti: str
    name: str
    scopes: list[str]
    created_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    active: bool


class ApiTokenCreated(BaseModel):
    token: str
    token_info: ApiTokenInfo


class ApiTokenList(BaseModel):
    tokens: list[ApiTokenInfo]


ImportFormat = Literal["auto", "json", "excel", "sql"]


class ImportRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    format: ImportFormat = "auto"
    batch_size: int = Field(default=500, ge=1, le=5000)
    limit: int = Field(default=0, ge=0)
    index: bool = True
    reset: bool = False
    zip_password: str | None = Field(default=None, max_length=256)
    sheet: str | None = Field(default=None, max_length=128)


class ImportJobOut(BaseModel):
    id: str
    source_path: str
    format: str
    status: str
    batch_size: int
    record_limit: int
    index_enabled: bool
    reset: bool
    processed: int
    imported: int
    indexed: int
    skipped: int
    failed: int
    message: str
    errors: list[str]
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ImportJobList(BaseModel):
    jobs: list[ImportJobOut]
