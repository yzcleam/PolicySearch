from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Document(Base):
    """Canonical document catalogue. OpenSearch only stores the search copy."""

    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    doc_number: Mapped[str] = mapped_column(String(128), index=True, default="")
    issuer: Mapped[str] = mapped_column(String(128), index=True, default="")
    region: Mapped[str] = mapped_column(String(64), index=True, default="")
    category: Mapped[str] = mapped_column(String(64), index=True, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)

    # Source-compatible PKUlaw fields. Legacy fields above remain for
    # compatibility with existing sample data and older clients.
    law_db_name: Mapped[str] = mapped_column(String(64), index=True, default="")
    detail_url: Mapped[str] = mapped_column(String(512), default="")
    province: Mapped[str] = mapped_column(String(512), index=True, default="")
    city: Mapped[str] = mapped_column(String(64), index=True, default="")
    county: Mapped[str] = mapped_column(String(64), index=True, default="")
    category_1: Mapped[str] = mapped_column(Text, default="")
    category_2: Mapped[str] = mapped_column(Text, default="")
    law_type: Mapped[str] = mapped_column(String(128), index=True, default="")
    pub_depart: Mapped[str] = mapped_column(Text, default="")
    pub_num: Mapped[str] = mapped_column(String(300), default="")
    pub_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    use_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    is_time: Mapped[str] = mapped_column(String(64), index=True, default="")
    detail_flag: Mapped[str] = mapped_column(Text, default="")
    detail_html: Mapped[str] = mapped_column(Text, default="")
    detail_md: Mapped[str] = mapped_column(Text, default="")
    add_time: Mapped[str] = mapped_column(String(64), default="")

    issue_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    content: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(512), default="")
    file_hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ApiToken(Base):
    """Revocable API token metadata. The JWT itself is never stored."""

    __tablename__ = "api_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ImportJob(Base):
    """Progress and result of a JSON / Excel / SQL import."""

    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_path: Mapped[str] = mapped_column(String(1024))
    format: Mapped[str] = mapped_column(String(16), default="auto")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    batch_size: Mapped[int] = mapped_column(Integer, default=500)
    record_limit: Mapped[int] = mapped_column(Integer, default=0)
    index_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reset: Mapped[bool] = mapped_column(Boolean, default=False)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    imported: Mapped[int] = mapped_column(Integer, default=0)
    indexed: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
