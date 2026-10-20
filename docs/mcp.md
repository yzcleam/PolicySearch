# MCP 服务

PolicySearcher 提供一个只读 MCP 服务，把现有检索 API 暴露为三个工具：

| 工具 | 用途 |
| --- | --- |
| `policy_search_documents` | 检索政策文档，返回摘要、分页、高亮和分面 |
| `policy_get_document` | 按 `doc_id` 获取完整正文 |
| `policy_get_stats` | 查看文档数、索引数、分词器和服务状态 |

MCP 服务不直接访问 PostgreSQL / OpenSearch，而是调用 FastAPI 的 `/api/*`，保证 Web UI、HTTP API 和 MCP 行为一致。

## 前置条件

1. 已完成 `npm run deploy`；
2. FastAPI 正在运行（`npm start`）；
3. `.env` 中的 `POLICY_API_URL` 指向 FastAPI，默认 `http://127.0.0.1:8000`。
4. 如果要调用 HTTP MCP，先在页面右上角 **管理员** 入口登录并创建一个 `policy:read` Token。

检查：

```bash
npm run doctor
```

## 鉴权

- `MCP_AUTH_REQUIRED=true`（默认）时，Streamable HTTP 端点要求：

  ```http
  Authorization: Bearer <token>
  ```

- Token 在管理员页面创建，可随时撤销。
- 管理员 JWT 也包含 `policy:read`，可用于临时调试，但推荐为 MCP 客户端单独创建 Token。
- stdio 是本地进程，不经过 MCP HTTP 鉴权；如果 FastAPI 设置了 `AUTH_REQUIRED=true`，需要在 MCP 客户端环境里配置 `POLICY_API_TOKEN`。

## 启动方式

### stdio（本地 MCP 客户端）

适合 Claude Desktop、OpenCode 等本地客户端。MCP 客户端直接启动 Python 进程，**不要通过 `npm run` 启动 stdio 服务**，因为 npm 会向 stdout 打印启动信息，可能破坏 JSON-RPC 通道。

通用配置：

```json
{
  "mcpServers": {
    "policysearcher": {
      "command": "<project>/.venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "<project>",
      "env": {
        "MCP_TRANSPORT": "stdio",
        "POLICY_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

Windows 下将 `command` 改为：

```text
<project>\.venv\Scripts\python.exe
```

也可以使用 Node 启动器：

```json
{
  "mcpServers": {
    "policysearcher": {
      "command": "node",
      "args": ["tools/mcp.mjs"],
      "cwd": "<project>"
    }
  }
}
```

启动器只写 stderr，不会污染 stdio 协议通道；它会读取根目录 `.env`。

### Streamable HTTP（远程部署）

在 `.env` 中设置：

```ini
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8765
MCP_PATH=/mcp
MCP_STATELESS=false
MCP_AUTH_REQUIRED=true
MCP_AUTOSTART=true
```

启动：

```bash
npm start
# 或只启动 MCP HTTP
npm run mcp:http
```

MCP 端点：

```text
http://127.0.0.1:8765/mcp
```

客户端请求需要带管理员页面创建的 Token：

```json
{
  "mcpServers": {
    "policysearcher-http": {
      "url": "http://127.0.0.1:8765/mcp",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

服务器部署时把 `MCP_HOST` 设为 `0.0.0.0`，并通过防火墙或反向代理暴露端口。

## 配置项

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MCP_TRANSPORT` | `stdio` | `stdio` / `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | HTTP 监听地址 |
| `MCP_PORT` | `8765` | HTTP 端口 |
| `MCP_PATH` | `/mcp` | Streamable HTTP 路径 |
| `MCP_STATELESS` | `false` | HTTP 无状态模式；当前客户端兼容性建议保持 false |
| `MCP_AUTH_REQUIRED` | `true` | HTTP 是否要求 Bearer Token |
| `MCP_AUTOSTART` | `true` | `npm start` 是否同时启动 MCP HTTP |
| `POLICY_API_TOKEN` | 空 | stdio MCP 在 API 开启鉴权时使用的服务 Token |
| `MCP_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `POLICY_API_URL` | `http://127.0.0.1:8000` | FastAPI 地址 |
| `POLICY_API_TIMEOUT` | `15` | API 超时秒数 |

## 调用示例

### 检索

```json
{
  "query": "增值税留抵退税",
  "mode": "smart",
  "filters": {
    "categories": ["税收优惠"],
    "date_from": "2020-01-01"
  },
  "page": 1,
  "size": 5
}
```

返回 `hits` 摘要、`facets` 分面和分页信息。完整正文需要再调用：

```json
{ "doc_id": "doc-000123" }
```

### 状态

`policy_get_stats` 无参数。

## 错误行为

成功时返回 `structuredContent`，并符合 `mcp_server/schemas/` 中的输出 Schema。

失败时：

- `isError: true`
- `content` 为错误文本，开头包含错误码：
  - `INVALID_ARGUMENT`
  - `UNAUTHORIZED`
  - `FORBIDDEN`
  - `NOT_FOUND`
  - `UPSTREAM_UNAVAILABLE`
  - `INTERNAL_ERROR`
- 不返回 `structuredContent`

## Schema 与设计

- [MCP Schema 设计](mcp-schema-v1.md)
- [完整 tools/list 示例](../mcp_server/tools-list.example.json)
- [输入 / 输出 JSON Schema](../mcp_server/schemas/)
