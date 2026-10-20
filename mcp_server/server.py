from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .auth import PolicyTokenVerifier
from .client import PolicyApiClient
from .models import (
    GetDocumentOutput,
    PolicyDocument,
    SearchFilters,
    SearchMode,
    SearchOutput,
    SortMode,
    StatsOutput,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger("policysearcher.mcp")

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} 必须是整数，当前值: {value!r}") from exc


API_URL = os.getenv("POLICY_API_URL") or "http://127.0.0.1:8000"
try:
    API_TIMEOUT = float(os.getenv("POLICY_API_TIMEOUT", "15"))
except ValueError as exc:
    raise SystemExit("POLICY_API_TIMEOUT 必须是数字，例如 15") from exc
MCP_HOST = os.getenv("MCP_HOST") or "127.0.0.1"
MCP_PORT = _env_int("MCP_PORT", 8765)
MCP_PATH = os.getenv("MCP_PATH") or "/mcp"
MCP_TRANSPORT = (os.getenv("MCP_TRANSPORT") or "stdio").strip().lower()
MCP_LOG_LEVEL = (os.getenv("MCP_LOG_LEVEL") or "INFO").strip().upper()
MCP_AUTH_REQUIRED = _env_bool("MCP_AUTH_REQUIRED", True)

if not MCP_PATH.startswith("/"):
    raise SystemExit("MCP_PATH 必须以 / 开头，例如 /mcp")
if not 1 <= MCP_PORT <= 65535:
    raise SystemExit("MCP_PORT 必须在 1-65535 之间")
if MCP_TRANSPORT not in {"stdio", "streamable-http"}:
    raise SystemExit("MCP_TRANSPORT 只能是 stdio 或 streamable-http")
if MCP_LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    raise SystemExit("MCP_LOG_LEVEL 必须是 DEBUG/INFO/WARNING/ERROR/CRITICAL")

client = PolicyApiClient(
    API_URL,
    timeout_seconds=API_TIMEOUT,
    default_token=os.getenv("POLICY_API_TOKEN") or None,
)


def _request_token() -> str | None:
    access = get_access_token()
    return access.token if access is not None else None


@asynccontextmanager
async def lifespan(_server: FastMCP):
    logger.info("MCP API upstream: %s", API_URL)
    try:
        yield
    finally:
        await client.close()


public_host = "127.0.0.1" if MCP_HOST in {"0.0.0.0", "::"} else MCP_HOST
auth_base = f"http://{public_host}:{MCP_PORT}"
auth_settings = None
token_verifier = None
if MCP_TRANSPORT == "streamable-http" and MCP_AUTH_REQUIRED:
    auth_settings = AuthSettings(
        issuer_url=auth_base,
        resource_server_url=auth_base,
        required_scopes=["policy:read"],
        validate_token_resource=False,
    )
    token_verifier = PolicyTokenVerifier(client)


mcp = FastMCP(
    "PolicySearcher",
    instructions=(
        "只读的中文政策文档检索服务。优先使用 policy_search_documents 检索摘要；"
        "需要引用原文或核对具体条款时，再用 policy_get_document 获取完整正文。"
        "不要调用管理接口修改或删除数据。"
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path=MCP_PATH,
    stateless_http=_env_bool("MCP_STATELESS", False),
    log_level=MCP_LOG_LEVEL,
    lifespan=lifespan,
    auth=auth_settings,
    token_verifier=token_verifier,
)


@mcp.tool(
    name="policy_search_documents",
    title="Search policy documents",
    description=(
        "检索中文政策文档。输入自然语言查询、检索模式、字段过滤和分页参数；"
        "返回文档摘要、分面统计和高亮片段。需要完整正文时，再调用 "
        "policy_get_document。query 为空时按 filters 浏览并按发布日期倒序返回。"
    ),
    annotations=READ_ONLY,
    structured_output=True,
)
async def policy_search_documents(
    query: Annotated[
        str,
        Field(
            description=(
                "自然语言或关键词查询。空字符串表示不限制关键词，仅按 filters "
                "浏览。示例：增值税留抵退税。"
            )
        ),
    ] = "",
    mode: Annotated[
        SearchMode,
        Field(
            description=(
                "检索模式。smart：短语+分词相关度+容错；keyword：BM25；"
                "exact：短语匹配；fuzzy：编辑距离容错。"
            )
        ),
    ] = "smart",
    filters: Annotated[
        SearchFilters | None,
        Field(description="精确匹配过滤条件；多个字段之间为 AND 关系。"),
    ] = None,
    page: Annotated[int, Field(ge=1, description="页码，从 1 开始。")] = 1,
    size: Annotated[
        int,
        Field(ge=1, le=50, description="每页返回条数，最大 50；MCP 场景建议 3-10。"),
    ] = 10,
    sort: Annotated[
        SortMode,
        Field(description="排序方式：相关度、发布日期倒序、发布日期正序。"),
    ] = "relevance",
    slop: Annotated[
        int,
        Field(ge=0, le=10, description="exact/smart 模式下短语允许的词间距。"),
    ] = 2,
) -> SearchOutput:
    effective_filters = filters or SearchFilters()
    payload = {
        "query": query,
        "mode": mode,
        "filters": effective_filters.model_dump(mode="json"),
        "page": page,
        "size": size,
        "sort": sort,
        "slop": slop,
    }
    data = await client.search(payload, token=_request_token())
    total = int(data.get("total", 0))
    has_more = page * size < total
    return SearchOutput.model_validate(
        {
            **data,
            "has_more": has_more,
            "next_page": page + 1 if has_more else None,
        }
    )


@mcp.tool(
    name="policy_get_document",
    title="Get policy document",
    description=(
        "按文档 ID 获取政策文档详情和完整正文。仅在需要引用原文或核对具体条款时"
        "调用；普通检索优先使用 policy_search_documents。"
    ),
    annotations=READ_ONLY,
    structured_output=True,
)
async def policy_get_document(
    doc_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=128,
            description="文档唯一标识，例如 doc-000123。",
        ),
    ],
) -> GetDocumentOutput:
    data = await client.get_document(doc_id, token=_request_token())
    return GetDocumentOutput(document=PolicyDocument.model_validate(data))


@mcp.tool(
    name="policy_get_stats",
    title="Get policy search stats",
    description=(
        "获取文档数、OpenSearch 索引数、索引体积、分词器和服务状态，"
        "用于判断检索服务是否可用。"
    ),
    annotations=READ_ONLY,
    structured_output=True,
)
async def policy_get_stats() -> StatsOutput:
    data = await client.stats(token=_request_token())
    return StatsOutput.model_validate(data)


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, MCP_LOG_LEVEL),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info(
        "Starting PolicySearcher MCP transport=%s upstream=%s",
        MCP_TRANSPORT,
        API_URL,
    )
    mcp.run(transport=MCP_TRANSPORT)


if __name__ == "__main__":
    main()
