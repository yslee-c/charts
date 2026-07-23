"""健康检查路由。"""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """存活探针 + 数据库连通性检查。"""
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "ok",
        "app": settings.app_name,
        "database": "ok" if db_ok else "error",
    }
