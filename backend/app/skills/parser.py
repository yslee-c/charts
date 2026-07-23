"""SKILL.md 解析 —— Claude Agent Skills 规范。

结构：
    ---
    name: my-skill
    description: 什么时候该用这个 skill
    kind: instruction            # 可选，默认 instruction；http 需配 http_action
    parameters:                  # 可选，tool 参数的 JSON Schema（http 型常用）
      type: object
      properties: {...}
    http_action:                 # kind=http 时必需
      method: GET
      url: https://api.example.com/path
    ---
    # 指令正文（Markdown）……
"""
import re

import yaml

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # 规范：小写字母/数字/连字符
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


class SkillParseError(ValueError):
    """SKILL.md 格式或字段不合法。"""


def parse_skill_md(text: str) -> dict:
    """解析 SKILL.md 文本，返回可用于创建 Skill 的字段字典。"""
    m = _FRONTMATTER_RE.match(text.lstrip("﻿").lstrip())
    if not m:
        raise SkillParseError(
            "缺少 YAML frontmatter（文件需以 `---` 开头并包含 name/description）。"
        )

    raw_meta, body = m.group(1), m.group(2).strip()
    try:
        meta = yaml.safe_load(raw_meta) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"frontmatter YAML 解析失败：{exc}") from exc
    if not isinstance(meta, dict):
        raise SkillParseError("frontmatter 必须是键值对。")

    name = str(meta.get("name", "")).strip()
    description = str(meta.get("description", "")).strip()
    if not name:
        raise SkillParseError("frontmatter 缺少 `name`。")
    if not _NAME_RE.match(name):
        raise SkillParseError(
            f"`name` 不合规范（需小写字母/数字/连字符，如 my-skill）：{name!r}"
        )
    if not description:
        raise SkillParseError("frontmatter 缺少 `description`（决定 agent 是否选用它）。")

    kind = str(meta.get("kind", "instruction")).strip() or "instruction"
    # native 型由系统内置（对应一个已注册的 Python handler），用户侧接口会拒绝创建
    if kind not in ("instruction", "http", "native"):
        raise SkillParseError(f"`kind` 仅支持 instruction / http / native：{kind!r}")

    parameters_schema = meta.get("parameters")
    if parameters_schema is not None and not isinstance(parameters_schema, dict):
        raise SkillParseError("`parameters` 必须是 JSON Schema 对象。")

    http_action = meta.get("http_action")
    if kind == "http":
        if not isinstance(http_action, dict):
            raise SkillParseError("kind=http 时必须提供 `http_action`（含 method/url）。")
        if not http_action.get("url"):
            raise SkillParseError("`http_action` 缺少 `url`。")
        http_action.setdefault("method", "GET")
    else:
        http_action = None

    return {
        "name": name,
        "description": description,
        "kind": kind,
        "parameters_schema": parameters_schema,
        "http_action": http_action,
        "skill_md": body,
    }


def render_skill_md(skill) -> str:
    """从 Skill 模型重建 SKILL.md 文本（供编辑器回填）。"""
    front: dict = {"name": skill.name, "description": skill.description}
    if skill.kind and skill.kind != "instruction":
        front["kind"] = skill.kind
    if skill.parameters_schema:
        front["parameters"] = skill.parameters_schema
    if skill.http_action:
        front["http_action"] = skill.http_action

    frontmatter = yaml.safe_dump(
        front, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    body = skill.skill_md or ""
    return f"---\n{frontmatter}---\n\n{body}".rstrip() + "\n"
