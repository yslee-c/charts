"""SkillRun —— 每次 skill 调用的审计记录，便于调试与观测。"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SkillRun(Base):
    __tablename__ = "skill_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    skill_name: Mapped[str] = mapped_column(String(128))  # 冗余存储，便于查询
    arguments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok|error
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
