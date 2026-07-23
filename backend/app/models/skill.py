"""Skill 模型 —— 采用 Claude Agent Skills 规范（SKILL.md）。

kind:
  - "instruction"：纯指令型。被调用时把 SKILL.md 正文注入上下文（渐进式披露）。
  - "http"：声明一个受控 HTTP 动作，被调用时执行外部 API 请求。
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 来自 SKILL.md frontmatter，规范要求为 slug（小写字母/数字/连字符）
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    # SKILL.md 正文（指令）—— 渐进式披露时才注入上下文
    skill_md: Mapped[str] = mapped_column(Text, default="")

    kind: Mapped[str] = mapped_column(String(32), default="instruction")
    # 供 LLM tool calling 的参数 JSON Schema（http 型使用；instruction 型可为空）
    parameters_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # http 型的动作配置：{"method","url"}；tool 参数按 GET->query / 其它->json body 发送
    http_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    source: Mapped[str] = mapped_column(String(32), default="manual")  # manual|import|builtin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否加入可用集合（“订阅”）
    version: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
