from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, String, Text, func
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
