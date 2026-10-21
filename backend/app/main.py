import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (register ORM metadata)
from .config import BASE_DIR, get_settings
from .database import engine
from .migrations import run_migrations
from .routers import admin, auth, documents, imports, search
from .services.index_service import index_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("policysearcher")

settings = get_settings()
FRONTEND_DIR = BASE_DIR / "frontend"

_started_at = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    schema_version = run_migrations(engine)
    log.info("数据库 schema v%s 就绪", schema_version)
    try:
        mode = index_service.ensure_index()
        log.info("OpenSearch 索引 %s 就绪 (analyzer=%s)", index_service.index, mode)
    except Exception as exc:  # pragma: no cover - allow API to boot degraded
        log.warning("OpenSearch 初始化失败: %s", exc)
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(auth.tokens_router)
app.include_router(imports.router)
app.include_router(search.router)
app.include_router(documents.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    os_online = index_service.ping()
    return {
        "status": "ok" if os_online else "degraded",
        "uptime_seconds": int(time.time() - _started_at),
        "engine": "postgresql+opensearch",
        "opensearch": "online" if os_online else "offline",
    }


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
