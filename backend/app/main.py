"""FastAPI 应用入口。

挂载 health / chat / skills 路由；启动时初始化数据库并植入内置 skill。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health, skills
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.services.skill_service import seed_builtins

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表（若迁移未跑）并植入内置 skill —— 二者皆幂等
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        added = seed_builtins(db)
        if added:
            logger.info("seeded %d builtin skills", added)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
app.include_router(skills.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/api/health"}
