"""数据库连接与会话。

约定：只用 SQLAlchemy 通用类型（如 JSON，而非 PG 专属 JSONB），
以便将来从 SQLite 平滑迁移到 PostgreSQL。
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# SQLite 需要 check_same_thread=False 才能在多线程（FastAPI）下使用
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类；Alembic 以 Base.metadata 为迁移目标。"""


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：按请求提供数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
