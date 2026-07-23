"""SKILL.md 解析与渲染测试。"""
from types import SimpleNamespace

import pytest

from app.skills.parser import SkillParseError, parse_skill_md, render_skill_md

INSTRUCTION = """\
---
name: my-skill
description: 当用户想做某事时使用
---

# 指令
做点什么。
"""

HTTP = """\
---
name: ip-geo
description: 查询 IP 归属
kind: http
parameters:
  type: object
  properties:
    ip: {type: string}
  required: [ip]
http_action:
  method: GET
  url: https://example.com/{ip}
---

# 正文
查询并返回。
"""


def test_parse_instruction():
    f = parse_skill_md(INSTRUCTION)
    assert f["name"] == "my-skill"
    assert f["kind"] == "instruction"
    assert f["http_action"] is None
    assert "做点什么" in f["skill_md"]


def test_parse_http():
    f = parse_skill_md(HTTP)
    assert f["kind"] == "http"
    assert f["http_action"]["method"] == "GET"
    assert f["http_action"]["url"].endswith("/{ip}")
    assert f["parameters_schema"]["required"] == ["ip"]


def test_missing_frontmatter():
    with pytest.raises(SkillParseError):
        parse_skill_md("no frontmatter here")


def test_bad_name():
    bad = INSTRUCTION.replace("name: my-skill", "name: Bad Name")
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_missing_description():
    bad = "---\nname: x\n---\n\nbody"
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_http_requires_action():
    bad = "---\nname: x\ndescription: y\nkind: http\n---\n\nbody"
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_render_roundtrip():
    """render(parse(x)) 再 parse，关键字段应一致。"""
    fields = parse_skill_md(HTTP)
    skill = SimpleNamespace(**fields)
    rendered = render_skill_md(skill)
    reparsed = parse_skill_md(rendered)
    assert reparsed["name"] == fields["name"]
    assert reparsed["kind"] == fields["kind"]
    assert reparsed["http_action"]["url"] == fields["http_action"]["url"]
    assert reparsed["parameters_schema"] == fields["parameters_schema"]
    assert reparsed["skill_md"].strip() == fields["skill_md"].strip()
