"""Skill 相关 DTO。"""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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
    """通过粘贴 / 上传 SKILL.md 文本导入或更新。"""

    content: str


class SkillCreate(BaseModel):
    """结构化新建 skill（供表单使用）。"""

    name: str
    description: str
    kind: Literal["instruction", "http"] = "instruction"
    skill_md: str = ""
    parameters_schema: dict | None = None
    http_action: dict | None = None

    @field_validator("name")
    @classmethod
    def _valid_name(cls, v: str) -> str:
        v = v.strip()
        if not _NAME_RE.match(v):
            raise ValueError("name 需为小写字母/数字/连字符，如 my-skill")
        return v

    @field_validator("description")
    @classmethod
    def _non_empty_desc(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description 不能为空")
        return v.strip()


class SkillActive(BaseModel):
    is_active: bool


class SkillRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int | None
    skill_name: str
    arguments: dict | None
    output: str
    status: str
    error: str | None
    latency_ms: int
    created_at: datetime
