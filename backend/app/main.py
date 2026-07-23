"""FastAPI 应用入口。

M0：仅提供健康检查，打通前后端与数据库连接。
后续里程碑将在此挂载 chat / skills 等路由。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    # 显式来源 + 本地开发正则（任意 localhost/127.0.0.1 端口，http/https 皆可），
    # 避免因 127.0.0.1 vs localhost 或端口不同导致的跨域拦截。
    allow_origins=[settings.frontend_origin],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/api/health"}
