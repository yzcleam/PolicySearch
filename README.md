# PolicySearcher

面向中文政策文本的检索服务原型。**PostgreSQL 保存文档目录与原文，OpenSearch 2.19 + IK 提供中文分词和倒排检索，FastAPI 提供 API 并托管零构建前端。**

当前仓库使用 320 份确定性示例数据，重点验证精确、短语、模糊与相关度检索链路；百万级容量验证、权限体系和 RAG 尚未完成。

![检索界面](docs/screenshot.png)

## 功能

- **四种检索模式**
  - `smart`：短语命中 + 分词相关度 + 编辑距离容错
  - `keyword`：BM25 关键词检索
  - `exact`：标题、摘要、正文短语匹配
  - `fuzzy`：`fuzziness=AUTO` 容错检索
- **字段过滤**：法规库、省份、城市、区县、一级/二级分类、法规类型、发布机关、时效性、发布日期范围、实施日期范围
- **分面统计**：按法规库、省份/城市/区县、分类、法规类型、发布机关、时效性聚合
- **结果体验**：高亮、得分、分页、排序、详情抽屉、原文链接
- **管理接口**：示例数据导入、按 PostgreSQL 重建索引、清空、运行状态
- **可重复部署**：Node 脚本负责环境检测、配置生成、依赖安装、容器启动和数据库迁移

## 架构

```text
浏览器
  │  FastAPI 托管的静态前端
  ▼
FastAPI
  ├── PostgreSQL 16        文档目录、原文、文号、机关、日期、标签（source of truth）
  └── OpenSearch 2.19.3    检索副本 + IK 中文分词 + 倒排索引（search copy）
        └── analysis-ik 2.19.3 + 自定义政策词典
```

- PostgreSQL 是唯一事实来源，保存完整正文。
- OpenSearch 只保存检索所需的副本，可随时从 PostgreSQL 全量重建。
- 前端使用原生 HTML/CSS/JS，无 Node 构建步骤。
- Node 仅用于部署编排和进程启动，不参与页面构建。

## 目录

```text
PolicySearcher/
├─ backend/
│  ├─ app/
│  │  ├─ config.py              # 配置（读取项目根目录 .env）
│  │  ├─ database.py            # SQLAlchemy engine / session
│  │  ├─ models.py              # documents 表
│  │  ├─ migrations.py          # schema_version 与轻量迁移器
│  │  ├─ auth.py                # JWT / Bearer Token / 管理员认证
│  │  ├─ schemas.py             # API 请求 / 响应模型
│  │  ├─ main.py                # FastAPI 入口
│  │  ├─ routers/               # search / documents / auth / admin
│  │  └─ services/
│  │     ├─ catalog.py          # PostgreSQL 批量 upsert / 查询 / 统计
│  │     ├─ index_service.py    # OpenSearch 索引、mapping、bulk、IK 探测
│  │     ├─ search_service.py   # 检索模式、过滤、分面、高亮
│  │     ├─ importer.py         # JSON / Excel / SQL 流式导入与字段映射
│  │     ├─ import_jobs.py      # 导入任务进度与后台执行
│  │     ├─ token_service.py    # API Token 创建 / 撤销 / 校验
│  │     └─ sample_data.py      # 确定性示例数据
│  ├─ scripts/
│  │  ├─ seed.py                # 示例数据导入
│  │  ├─ import_data.py          # JSON / Excel / SQL 政策数据导入
│  │  ├─ migrate.py             # 数据库迁移入口
│  │  └─ *_test.py              # 检索 / 分词 / API 手工测试脚本
│  └─ requirements.txt
├─ deploy/opensearch/
│  ├─ Dockerfile                # OpenSearch + IK 镜像
│  ├─ opensearch-analysis-ik-2.19.3.zip
│  └─ ik-config/config/         # IK 词典与 IKAnalyzer.cfg.xml
├─ frontend/                    # index.html / styles.css / app.js / admin.css
├─ tools/                       # npm 部署与运维脚本
│  ├─ deploy.mjs
│  ├─ start.mjs
│  ├─ doctor.mjs
│  ├─ infra.mjs
│  ├─ seed.mjs
│  ├─ import.mjs
│  ├─ migrate.mjs
│  └─ lib.mjs
├─ mcp_server/                  # MCP 服务与 Input / Output Schema
├─ scripts/                     # 可选：Windows / WSL 辅助脚本
├─ docs/                        # 截图、MCP Schema 与 Windows/WSL 说明
├─ docker-compose.yml
├─ package.json
├─ package-lock.json
├─ .env.example
├─ .nvmrc
├─ .gitignore
└─ .gitattributes
```

## 快速开始

### 环境要求

| 依赖 | 要求 | 说明 |
| --- | --- | --- |
| Node.js | **≥ 20，建议 22** | npm 随 Node 安装；仓库含 `.nvmrc` |
| Python | **3.10+** | Linux 需安装 `python3-venv` / `python3-pip`；部署脚本创建平台专属虚拟环境（Windows `.venv` / Linux `.venv-linux`）并安装后端依赖 |
| Docker | Engine + Compose v2 | Linux / macOS 使用原生 Docker；Windows 可用 Docker Desktop 或 WSL 内的 Docker |

> Node、Python、Docker 属于宿主机前置环境，不会被 npm 自动安装。

### 部署

```bash
npm run deploy
```

> npm 没有 `npm deploy` 这个内置命令，请使用 **`npm run deploy`**。

部署向导会询问监听地址、应用端口、PostgreSQL 端口/账号/密码/数据库名、OpenSearch 端口与索引名、示例数据条数等。随后脚本会：

1. 检测 Node、Python、Docker、Compose、端口和磁盘空间；
2. 生成项目根目录 `.env`（已被 `.gitignore` 忽略）；
3. 创建平台专属 Python 虚拟环境（Windows `.venv` / Linux `.venv-linux`）并安装 `backend/requirements.txt`；
4. 启动 PostgreSQL 与 OpenSearch + IK 容器；
5. 等待数据库和 OpenSearch 通过健康检查；
6. 执行数据库迁移并记录 `schema_version`；
7. 数据库为空时导入示例数据，已有数据则跳过。

Python 依赖默认通过 `PIP_INDEX_URL` 使用清华 PyPI 镜像；服务器网络不同可改为内网镜像或官方源：

```ini
PIP_INDEX_URL=https://pypi.org/simple
```

Docker 镜像默认使用 `DOCKER_MIRROR=m.daocloud.io/docker.io`。如果服务器无法访问 Docker Hub 或该镜像，可改为内网仓库，或显式覆盖：

```ini
DOCKER_MIRROR=
POSTGRES_IMAGE=your-registry/postgres:16-alpine
OPENSEARCH_BASE_IMAGE=your-registry/opensearchproject/opensearch:2.19.3
```

非交互部署：

```bash
npm run deploy -- --yes
```

常用参数：

| 参数 | 作用 |
| --- | --- |
| `--yes` | 使用现有 `.env` 或默认值，不进入交互 |
| `--port 8001` | 覆盖应用端口 |
| `--force` | 覆盖已有 `.env` |
| `--skip-install` | 跳过 pip 安装，但检查依赖是否已存在 |
| `--skip-build` | 不重新构建 OpenSearch/IK 镜像 |
| `--skip-seed` | 不导入示例数据 |
| `--reset` | 清空现有文档并重新导入示例数据 |
| `--upgrade` | 升级 Python 依赖并重建镜像 |

### 启动

```bash
npm start
```

`npm start` 会读取 `.env`，确保容器运行，等待 FastAPI 健康，然后按 `APP_HOST` / `APP_PORT` 启动 FastAPI，并在 `MCP_AUTOSTART=true` 时同时启动 MCP Streamable HTTP。

临时换端口：

```bash
npm start -- --port 8010
```

不启动容器（例如数据库由外部提供）：

```bash
npm start -- --no-infra
```

不启动 MCP（只启动 FastAPI）：

```bash
npm start -- --no-mcp
```

停止 FastAPI / MCP 用 `Ctrl+C`；容器会保持运行。停止容器：

```bash
npm run infra:down
```

### 常用命令

| 命令 | 作用 |
| --- | --- |
| `npm run deploy` | 部署或更新配置 |
| `npm start` | 按 `.env` 启动服务 |
| `npm run doctor` | 检查 Node / Python / Docker / 端口 / 服务 |
| `npm run mcp:http` | 启动 MCP Streamable HTTP 服务 |
| `npm run migrate` | 检查并应用数据库迁移 |
| `npm run seed -- 320` | 数据库为空时导入示例数据 |
| `npm run seed -- 320 --reset` | 清空并重新导入示例数据 |
| `npm run import -- <path> --format json` | 导入 JSON / Excel / SQL 政策数据 |
| `npm run infra:up` | 启动并构建容器 |
| `npm run infra:down` | 停止容器（保留数据卷） |
| `npm run infra:status` | 查看容器状态 |
| `npm run infra:logs` | 查看最近容器日志 |
| `npm run infra:restart` | 重启容器 |
| `npm run infra:pull` | 拉取基础镜像 |

### 管理员与 Token

页面右上角 **管理员** 入口提供：

- 管理员 JWT 登录
- 创建 / 查看 / 撤销 API Token
- JSON / Excel / SQL 导入任务与进度
- 导入示例数据、重建索引、清空数据

初始管理员密码由 `npm run deploy` 生成并只打印一次。密码丢失时，清空 `.env` 中的 `ADMIN_PASSWORD_HASH` 后重新运行 `npm run deploy` 生成新密码。

### MCP 服务

MCP 服务调用现有 FastAPI，不直接复制检索逻辑。`npm start` 默认同时启动 FastAPI 和 MCP HTTP；也可以单独启动：

```bash
npm start
# 或只启动 MCP HTTP
npm run mcp:http
```

HTTP 默认启用 Bearer JWT 鉴权（`MCP_AUTH_REQUIRED=true`）。在页面右上角 **管理员** 入口登录后，创建 `policy:read` Token，并把它作为 MCP 客户端的 `Authorization: Bearer <token>` 请求头。

stdio 模式供本地 MCP 客户端直接启动 Python 进程，不要通过 `npm run` 启动，避免 npm 输出污染 JSON-RPC 通道。

工具、鉴权、客户端配置和 Schema 见 [docs/mcp.md](docs/mcp.md)。

### Windows / WSL

如果 Windows 上无法使用 Docker Desktop，可在 WSL2 发行版中运行 Docker Engine，并设置：

```ini
DOCKER_MODE=wsl
WSL_DISTRO=Ubuntu
```

详细步骤见 [docs/windows-wsl.md](docs/windows-wsl.md)。`scripts/start-stack.ps1` / `stop-stack.ps1` 是保留的 Windows 辅助脚本，新环境建议优先使用 npm 脚本。

## 配置

`npm run deploy` 会在项目根目录生成 `.env`。`.env` 包含本地密码，已被 `.gitignore` 忽略，不要提交。

主要变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_HOST` | `127.0.0.1` | 监听地址；服务器可设为 `0.0.0.0` |
| `APP_PORT` | `8000` | FastAPI 端口 |
| `CORS_ORIGINS` | `*` | 逗号分隔的来源 |
| `POSTGRES_HOST` | `127.0.0.1` | PostgreSQL 主机 |
| `POSTGRES_PORT` | `5432` | 宿主机映射端口 |
| `POSTGRES_USER` | `policy` | 数据库用户 |
| `POSTGRES_PASSWORD` | 部署时生成/保留 | 数据库密码 |
| `POSTGRES_DB` | `policy_search` | 数据库名 |
| `DATABASE_URL` | 自动生成 | SQLAlchemy 连接串 |
| `DOCKER_MIRROR` | `m.daocloud.io/docker.io` | Docker 镜像前缀；置空则用官方源 |
| `POSTGRES_IMAGE` | `m.daocloud.io/.../postgres:16-alpine` | PostgreSQL 镜像 |
| `OPENSEARCH_URL` | `http://127.0.0.1:9200` | OpenSearch 地址 |
| `OPENSEARCH_INDEX` | `policy_documents` | 索引名 |
| `OPENSEARCH_JAVA_OPTS` | `-Xms1g -Xmx1g` | 单节点堆内存 |
| `OPENSEARCH_IMAGE` | `policysearcher/opensearch-ik:2.19.3` | IK 镜像 |
| `OPENSEARCH_BASE_IMAGE` | `m.daocloud.io/.../opensearch:2.19.3` | 构建基础镜像 |
| `SEED_COUNT` | `320` | 示例数据条数 |
| `SEED_ON_DEPLOY` | `true` | 部署时是否导入 |
| `PIP_INDEX_URL` | `https://pypi.tuna.tsinghua.edu.cn/simple` | 部署时 pip 使用的 PyPI 镜像 |
| `DOCKER_MODE` | `auto` | `auto` / `local` / `wsl` |
| `WSL_DISTRO` | `Ubuntu` | WSL Docker 发行版 |
| `TZ` | `Asia/Shanghai` | 容器时区 |
| `JWT_SECRET` | 部署时生成 | JWT 签名密钥 |
| `JWT_EXPIRE_MINUTES` | `480` | 管理员会话有效期 |
| `ADMIN_USERNAME` | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD_HASH` | 部署时生成 | PBKDF2 管理员密码哈希 |
| `API_TOKEN_EXPIRE_DAYS` | `90` | API Token 默认有效期 |
| `AUTH_REQUIRED` | `false` | 为 true 时检索/文档/状态 API 也要求 Bearer Token |
| `MCP_TRANSPORT` | `stdio` | `stdio` / `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | MCP HTTP 监听地址 |
| `MCP_PORT` | `8765` | MCP HTTP 端口 |
| `MCP_PATH` | `/mcp` | MCP HTTP 路径 |
| `MCP_STATELESS` | `false` | HTTP 无状态模式；当前建议保持 false |
| `MCP_AUTH_REQUIRED` | `true` | MCP HTTP 是否要求 Bearer Token |
| `MCP_AUTOSTART` | `true` | `npm start` 是否同时启动 MCP HTTP |
| `POLICY_API_TOKEN` | 空 | stdio MCP 在 API 开启鉴权时使用的服务 Token |
| `POLICY_API_URL` | `http://127.0.0.1:<APP_PORT>` | MCP 调用的 FastAPI 地址 |
| `POLICY_API_TIMEOUT` | `15` | MCP 调用 API 超时秒数 |

注意：

- 修改 PostgreSQL 密码不会自动修改已有数据卷中的角色密码。已有数据卷时应保留原密码，或先备份并执行 `ALTER ROLE`；删除数据卷会丢失数据。
- 默认镜像通过 `DOCKER_MIRROR` 走 `m.daocloud.io/docker.io` 前缀；服务器无法访问该镜像时，可设置 `DOCKER_MIRROR=` 并显式指定 `POSTGRES_IMAGE`、`OPENSEARCH_BASE_IMAGE`。
- 服务器部署建议将 `APP_HOST` 设为 `0.0.0.0`，并配置防火墙或反向代理。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/search` | 检索 |
| `GET` | `/api/documents/{doc_id}` | 文档详情（含完整正文） |
| `GET` | `/api/stats` | 文档数、索引数、索引体积、分词器、状态 |
| `POST` | `/api/auth/login` | 管理员登录，返回 JWT |
| `GET` | `/api/auth/me` | 当前管理员信息 |
| `GET` | `/api/auth/verify` | 校验 Bearer Token，供 MCP 使用 |
| `GET` | `/api/admin/tokens` | 列出 API Token（管理员） |
| `POST` | `/api/admin/tokens` | 创建 API Token（管理员，Token 只返回一次） |
| `DELETE` | `/api/admin/tokens/{jti}` | 撤销 API Token（管理员） |
| `POST` | `/api/admin/import` | 启动 JSON / Excel / SQL 导入任务（管理员） |
| `GET` | `/api/admin/import` | 查看导入任务列表（管理员） |
| `GET` | `/api/admin/import/{job_id}` | 查看导入进度（管理员） |
| `POST` | `/api/admin/seed` | 导入示例数据（管理员） |
| `POST` | `/api/admin/reindex` | 按 PostgreSQL 全量重建 OpenSearch 索引（管理员） |
| `POST` | `/api/admin/clear` | 清空文档与索引（管理员） |
| `GET` | `/api/health` | 服务与 OpenSearch 健康状态 |

管理员接口必须携带管理员 JWT。`AUTH_REQUIRED=false` 时检索、文档、状态接口公开；设为 `true` 后也需要 `policy:read` Token。

MCP 使用见 [docs/mcp.md](docs/mcp.md)，Input / Output Schema 设计见 [docs/mcp-schema-v1.md](docs/mcp-schema-v1.md)。

### 检索请求

```json
{
  "query": "增值税留抵退税",
  "mode": "smart",
  "filters": {
    "law_db_names": [],
    "provinces": ["北京市"],
    "cities": [],
    "counties": [],
    "category_1": ["税收优惠"],
    "category_2": [],
    "law_types": [],
    "pub_departments": [],
    "pub_nums": [],
    "time_statuses": ["现行有效"],
    "pub_date_from": "2020-01-01",
    "pub_date_to": null,
    "use_date_from": null,
    "use_date_to": null
  },
  "page": 1,
  "size": 10,
  "sort": "relevance",
  "slop": 2
}
```

- `mode`：`smart` / `keyword` / `exact` / `fuzzy`
- `sort`：`relevance` / `date_desc` / `date_asc`
- `slop`：精确短语允许的词间距，默认 2

### 检索响应（节选）

```json
{
  "total": 17,
  "page": 1,
  "size": 10,
  "took_ms": 18,
  "mode": "smart",
  "query": "增值税留抵退税",
  "hits": [
    {
      "doc_id": "pkulaw-1",
      "title": "关于优化增值税留抵退税的意见",
      "doc_number": "国办发〔2024〕12号",
      "issuer": "国务院",
      "region": "全国",
      "category": "税收优惠",
      "tags": ["减税降费", "惠企政策"],
      "issue_date": "2024-05-10",
      "law_db_name": "lar",
      "detail_url": "8ef46f8ae2b7ce1207961d9a013f7286bdfb",
      "province": "北京市",
      "city": "北京市",
      "county": "",
      "category_1": "税收优惠",
      "category_2": "增值税留抵退税",
      "law_type": "地方性法规",
      "pub_depart": "国务院",
      "pub_num": "国办发〔2024〕12号",
      "pub_date": "2024-05-10",
      "use_date": "2024-06-01",
      "is_time": "现行有效",
      "add_time": "2024-05-11",
      "score": 65.20734,
      "highlights": [
        { "field": "title", "text": "关于优化<mark>增值税留抵退税</mark>的意见" }
      ]
    }
  ],
  "facets": {
    "issuers": [{ "value": "国务院", "count": 8 }],
    "categories": [{ "value": "税收优惠", "count": 17 }],
    "regions": [{ "value": "全国", "count": 9 }],
    "tags": [{ "value": "减税降费", "count": 7 }],
    "law_db_names": [{ "value": "lar", "count": 17 }],
    "provinces": [{ "value": "北京市", "count": 6 }],
    "cities": [{ "value": "北京市", "count": 6 }],
    "counties": [],
    "category_1": [{ "value": "税收优惠", "count": 17 }],
    "category_2": [{ "value": "增值税留抵退税", "count": 5 }],
    "law_types": [{ "value": "地方性法规", "count": 9 }],
    "pub_departments": [{ "value": "国务院", "count": 8 }],
    "time_statuses": [{ "value": "现行有效", "count": 17 }]
  }
}
```

## 数据导入

支持三种格式：

| 格式 | 输入 | 说明 |
| --- | --- | --- |
| JSON | `.json` / `.zip` | 支持顶层数组，或 `{"RECORDS": [...]}` / `{"records": [...]}` |
| Excel | `.xlsx` / `.xlsm` / `.zip` | 读取第一个工作表，第一行为表头 |
| SQL | `.sql` / `.zip` | 解析 MySQL `INSERT INTO ... VALUES (...)`，支持多行 VALUES |

### CLI

```bash
npm run import -- "/path/to/data.json" --format json
npm run import -- "/path/to/data.xlsx" --format excel
npm run import -- "/path/to/data.sql.zip" --format sql --zip-password "***"
```

也可以直接调用 Python：

```bash
python backend/scripts/import_data.py "/path/to/data.json" --format json
```

常用参数：

```text
--limit 1000          只导入前 1000 条，适合先验证
--batch-size 500      PostgreSQL / OpenSearch 批大小
--reset               导入前清空已有文档和索引
--no-index            只写 PostgreSQL，之后用管理接口重建索引
--zip-password        加密 ZIP 的密码
--sheet               指定 Excel 工作表
```

`--no-index` 不会清理或更新 OpenSearch；如果同时使用 `--reset`，重置后需要重新建立索引。

### 管理接口

管理员登录后可调用：

```http
POST /api/admin/import
Content-Type: application/json
Authorization: Bearer <admin-jwt>

{
  "path": "/path/to/data.json",
  "format": "json",
  "batch_size": 500,
  "limit": 0,
  "index": true,
  "reset": false,
  "zip_password": null
}
```

任务异步执行，返回 `job_id`，通过：

```http
GET /api/admin/import/{job_id}
```

查看进度。管理页面也提供“数据导入”表单，适合导入较小的 JSON / Excel 文件；大文件建议使用 CLI。

### 字段映射

导入器会把常见字段映射到 `documents`：

| 源字段 | 目标字段 |
| --- | --- |
| `id` / `doc_id` | `doc_id`（数字 id 加 `pkulaw-` 前缀） |
| `title` / `标题` | `title` |
| `pub_num` / `doc_number` / `文号` | `doc_number` |
| `pub_depart` / `issuer` / `发布机关` | `issuer` |
| `province` / `region` / `地区` | `region` |
| `category_1` / `category` | `category` |
| `tags` / `category_1` / `category_2` / `law_type` | `tags` |
| `pub_date` / `issue_date` / `发布日期` | `issue_date` |
| `use_date` / `effective_date` / `实施日期` | `effective_date` |
| `detail_md` / `detail_flag` / `detail_html` / `content` | `content` |
| `summary` / `摘要` | `summary` |
| `detail_url` / `source_url` / `url` | `source_url` |
| `is_time` / `status` | `status`（“现行有效”映射为 `active`） |

JSON 中的 `detail_md`、`detail_flag`、`detail_html` 会依次作为正文候选；HTML 会转成纯文本。

### 大规模导入

当前样本中的 JSON / SQL 压缩包接近 90GB，建议：

1. 先用 `--limit 1000` 验证字段和分词；
2. 用 `--no-index` 只写 PostgreSQL；
3. 数据落库后，再通过管理接口 `/api/admin/reindex` 或 `npm run seed -- 320 --reset` 之外的重建流程建立索引；
4. 根据服务器磁盘和 OpenSearch 堆内存分批导入。

SQL 压缩包如果加密，必须提供 `--zip-password`。Excel 目前只支持 `.xlsx` / `.xlsm`，不解析旧版 `.xls`。

### 检索字段

前端筛选、检索结果、MCP 工具字段已与 PKUlaw SQL 字段对齐：

```text
law_db_name, province, city, county,
category_1, category_2, law_type,
pub_depart, pub_num, pub_date, use_date,
is_time, detail_url, detail_md
```

`doc_number`、`issuer`、`region`、`category`、`issue_date`、`effective_date` 等旧字段仍然保留，用于兼容已有数据和旧客户端。

前端筛选：

- 法规库、省份、城市、区县
- 一级分类、二级分类
- 法规类型、发布机关、时效性
- 发布日期范围、实施日期范围

MCP 的 `policy_search_documents` 输入过滤器和输出 `hits` 使用同一组字段；完整字段见 [docs/mcp-schema-v1.md](docs/mcp-schema-v1.md)。

## 索引与 IK

索引 mapping 位于 `backend/app/services/index_service.py`：

- `title` / `summary` / `content`：`text`
  - 写入分析器：`policy_index`（`ik_max_word`）
  - 查询分析器：`policy_search`（`ik_smart`）
- `doc_number` / `issuer` / `region` / `category` / `tags` / `status`：`keyword`
- `issue_date` / `effective_date`：`date`
- `dynamic: strict`：未知字段会被拒绝

IK 词典位于 `deploy/opensearch/ik-config/config/`：

```text
IKAnalyzer.cfg.xml     # ext_dict = custom.dic
custom.dic             # 政策领域自定义词
main.dic / stopword.dic / ...
```

修改词典后需要重建 OpenSearch 镜像并重建索引：

```bash
npm run infra:up
npm run seed -- 320 --reset
```

验证分词：

```bash
.venv-linux/bin/python backend/scripts/analyze_test.py
```

Windows 下 Python 路径为 `.venv\Scripts\python.exe`；Linux / macOS 为 `.venv-linux/bin/python`。

## 数据库版本

- `backend/app/migrations.py` 维护 `SCHEMA_VERSION`。
- 启动或执行 `npm run migrate` 时会创建缺失表、确保 `app_meta` 存在、读取 `schema_version`，并按 `MIGRATIONS` 顺序应用迁移。
- 如果数据库版本高于程序支持版本，会拒绝启动，避免旧代码破坏新数据。

新增迁移：

```python
MIGRATIONS: dict[int, Callable[[Connection], None]] = {
    2: _migrate_v2_add_column,
}
```

然后将 `SCHEMA_VERSION` 改为 `2`，部署时自动执行一次。

## 开发与测试

```bash
npm run doctor
npm run migrate
npm run seed -- 320
npm run seed -- 320 --reset
```

后端测试脚本：

```bash
.venv-linux/bin/python backend/scripts/search_test.py
.venv-linux/bin/python backend/scripts/analyze_test.py
.venv-linux/bin/python backend/scripts/http_test.py
```

Windows 下将 `.venv-linux/bin/python` 换成 `.venv\Scripts\python.exe`。

## 已知限制

- 示例数据为 320 篇；JSON / Excel / SQL 导入已支持，但尚未完成百万级容量验证。
- OpenSearch 当前为单节点、单分片、0 副本、1GB heap；生产环境需要多分片、副本和独立数据盘。
- 已有管理员 JWT 和 API Token，但尚未接入细粒度角色与文档级权限。
- 尚无 PDF/Word/HTML 批量导入 UI、任务队列和去重流水线。
- 尚未接入 embedding、向量库与 RAG 重排。

## Roadmap

1. 文件解析 → 清洗 → 去重 → PostgreSQL 落库 → 批量写 OpenSearch。
2. 索引治理：分片/副本、`refresh_interval`、`_bulk` 分批、`search_after` 深分页。
3. 权限、审计、敏感词与脱敏。
4. 前端管理台：上传、解析预览、分块编辑、任务状态。
5. 精确检索稳定后接入 embedding、向量检索与重排。
