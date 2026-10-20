# MCP 服务 Schema 设计 v1

本文定义 PolicySearcher 搜索服务的 MCP 工具边界。v1 只暴露**只读检索能力**，不暴露导入、重建索引、清空等管理操作。

## 工具集合

| 工具名 | 用途 | 对应现有 API |
| --- | --- | --- |
| `policy_search_documents` | 检索政策文档，返回摘要、分页和高亮 | `POST /api/search` |
| `policy_get_document` | 按 ID 获取完整政策正文 | `GET /api/documents/{doc_id}` |
| `policy_get_stats` | 查看文档数、索引数、分词器与状态 | `GET /api/stats` |

不暴露 `POST /api/admin/*`，避免模型误删数据或重建索引。

## 完整 Schema 文件

- [检索输入](../mcp_server/schemas/policy_search_documents.input.json)
- [检索输出](../mcp_server/schemas/policy_search_documents.output.json)
- [文档详情输入](../mcp_server/schemas/policy_get_document.input.json)
- [文档详情输出](../mcp_server/schemas/policy_get_document.output.json)
- [状态输入](../mcp_server/schemas/policy_get_stats.input.json)
- [状态输出](../mcp_server/schemas/policy_get_stats.output.json)
- [tools/list 完整示例](../mcp_server/tools-list.example.json)

实现时应将对应 Schema **内联**到 MCP 工具定义的 `inputSchema` / `outputSchema` 中，而不是依赖客户端解析相对路径。

## 工具定义示例

```json
{
  "name": "policy_search_documents",
  "title": "Search policy documents",
  "description": "检索中文政策文档。输入自然语言查询、模式、字段过滤和分页参数；返回文档摘要、分面统计和高亮片段。需要完整正文时，再用 policy_get_document。",
  "inputSchema": { "$ref": "policy_search_documents.input.json" },
  "outputSchema": { "$ref": "policy_search_documents.output.json" },
  "annotations": {
    "readOnlyHint": true,
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false
  }
}
```

> `$ref` 仅用于本文展示。实际 MCP 工具定义应展开为完整 JSON Schema。

## 检索输入设计

### 查询与模式

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `query` | string | `""` | 空字符串表示仅按 filters 浏览；非空时执行检索 |
| `mode` | enum | `smart` | `smart` / `keyword` / `exact` / `fuzzy` |
| `slop` | integer | `2` | 0-10，仅 `exact` / `smart` 生效 |

说明：

- MCP 默认使用 `smart`，因为这是面向自然语言查询的场景；底层 API 默认是 `keyword`，实现时必须显式传参，避免依赖两套默认值。
- `query` 允许为空，支持“按机关/地区/日期浏览”的工作流。
- `slop` 限制在 0-10，防止短语查询过度扩散。

### 过滤条件

```json
{
  "filters": {
    "issuers": ["国务院"],
    "categories": ["税收优惠"],
    "regions": ["全国"],
    "tags": ["减税降费"],
    "date_from": "2020-01-01",
    "date_to": "2024-12-31"
  }
}
```

- 四个数组字段为 OR（同一字段内）语义，字段之间为 AND。
- 日期使用 ISO 8601 `date`，只过滤 `issue_date`。
- 每个数组最多 20 项，避免生成过大的 OpenSearch terms query。
- 数组元素不允许空字符串。

### 分页与排序

| 字段 | 类型 | 默认 | 约束 |
| --- | --- | --- | --- |
| `page` | integer | `1` | 最小 1 |
| `size` | integer | `10` | 1-50；MCP 建议 3-10 |
| `sort` | enum | `relevance` | `relevance` / `date_desc` / `date_asc` |

## 检索输出设计

`policy_search_documents` 返回摘要列表，不返回完整正文，避免单次工具调用把上下文撑爆。完整正文通过 `policy_get_document` 获取。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `total` | integer | 分页前总数 |
| `page` / `size` | integer | 回显分页参数 |
| `took_ms` | integer | OpenSearch 查询耗时 |
| `mode` / `query` | string | 回显查询 |
| `has_more` | boolean | `page * size < total` |
| `next_page` | integer/null | 有下一页时为 `page + 1`，否则 `null` |
| `hits` | array | 文档摘要列表 |
| `facets` | object | 机关、类型、地区、标签聚合 |

### `hits` 单项

包含 `doc_id`、`title`、`doc_number`、`issuer`、`region`、`category`、`tags`、`issue_date`、`effective_date`、`summary`、`source_url`、`status`、`score`、`highlights`。

- `issue_date` / `effective_date` 未知时为 `null`。
- `score` 为 `number | null`。
- `highlights[].text` 保留 `<mark>...</mark>` 标记。
- `summary` 可能为空字符串，不能假设一定有内容。

### `facets`

固定包含：

```json
{
  "issuers": [{ "value": "国务院", "count": 8 }],
  "categories": [{ "value": "税收优惠", "count": 17 }],
  "regions": [{ "value": "全国", "count": 9 }],
  "tags": [{ "value": "减税降费", "count": 7 }]
}
```

每个 bucket 的 `value` 为字符串，`count` 为大于等于 1 的整数；无结果时数组为空。

## 文档详情工具

### 输入

```json
{ "doc_id": "doc-000123" }
```

### 输出

```json
{
  "document": {
    "doc_id": "doc-000123",
    "title": "关于优化增值税留抵退税的意见",
    "doc_number": "国办发〔2024〕12号",
    "issuer": "国务院",
    "region": "全国",
    "category": "税收优惠",
    "tags": ["减税降费"],
    "issue_date": "2024-05-10",
    "effective_date": null,
    "summary": "...",
    "source_url": "",
    "status": "active",
    "content": "政策正文全文...",
    "file_hash": "...",
    "created_at": "2024-05-10T12:00:00"
  }
}
```

`content` 是完整正文，可能很长；工具描述应明确提示“仅在需要引用原文时调用”。

## 状态工具

`policy_get_stats` 无输入参数，返回：

```json
{
  "documents": 320,
  "index_docs": 320,
  "index_size_bytes": 694928,
  "analyzer": "ik",
  "engine": "postgresql + opensearch",
  "status": "ready"
}
```

用于模型判断检索服务是否可用，不用于业务检索。

## 错误契约

MCP 成功响应：

- `structuredContent`：必须符合对应 `outputSchema`
- `content`：FastMCP 自动生成的 JSON 文本；客户端应优先读取 `structuredContent`

MCP 失败响应：

- `isError: true`
- 不返回 `structuredContent`
- `content` 为错误文本，开头包含错误码；当前 FastMCP 会在前面加上
  `Error executing tool ...`，但错误码仍然保留：

```text
Error executing tool policy_get_document: NOT_FOUND: 文档不存在
```

错误码：

| 错误码 | 场景 |
| --- | --- |
| `INVALID_ARGUMENT` | 参数不合法、分页越界、日期格式错误 |
| `UNAUTHORIZED` | Bearer Token 无效或已过期 |
| `FORBIDDEN` | Token 缺少所需 scope |
| `NOT_FOUND` | `doc_id` 不存在 |
| `UPSTREAM_UNAVAILABLE` | PostgreSQL / OpenSearch 不可用 |
| `INTERNAL_ERROR` | 未预期异常 |

不向模型返回堆栈、连接串、密码或 OpenSearch 原始错误体。

## 与现有 API 的映射

| MCP 参数 | FastAPI 参数 |
| --- | --- |
| `query` | `query` |
| `mode` | `mode` |
| `filters.issuers` | `filters.issuers` |
| `filters.categories` | `filters.categories` |
| `filters.regions` | `filters.regions` |
| `filters.tags` | `filters.tags` |
| `filters.date_from` | `filters.date_from` |
| `filters.date_to` | `filters.date_to` |
| `page` / `size` / `sort` / `slop` | 同名参数 |

服务端补充计算：

```text
has_more = page * size < total
next_page = has_more ? page + 1 : null
```

## 实现

- **语言**：Python（FastMCP），与现有 FastAPI 后端同栈。
- **代码**：`mcp_server/server.py`、`mcp_server/models.py`、`mcp_server/client.py`。
- **传输**：本地/桌面客户端用 stdio；远程部署用 Streamable HTTP。
- **调用方式**：MCP 服务调用 FastAPI 的 `/api/*`，不直接复制检索逻辑，保证 Web 与 MCP 行为一致。
- **超时**：对 API 调用设置 15 秒超时；连接失败返回 `UPSTREAM_UNAVAILABLE`。
- **只读**：v1 不提供 seed/reindex/clear 工具。
- **启动**：本地客户端直接启动 `.venv` 中的 Python；HTTP 模式可用 `npm run mcp:http`。
