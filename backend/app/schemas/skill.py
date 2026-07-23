"""Skill 相关 DTO。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    kind: str
    skill_md: str
    parameters_schema: dict | None = None
    http_action: dict | None = None
    source: str
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class SkillImport(BaseModel):
    """通过粘贴 / 上传 SKILL.md 文本导入。"""

    content: str


class SkillActive(BaseModel):
    is_active: bool
