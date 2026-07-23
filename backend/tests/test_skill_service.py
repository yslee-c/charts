"""skill_service 单元测试（裸库，无内置 skill）。"""
import pytest

from app.services import skill_service as svc
from app.services.skill_service import SkillNameConflict
from app.skills.parser import SkillParseError

SKILL_MD = """\
---
name: greeter
description: 打招呼
---

# 问候
说你好。
"""


def test_create_from_skill_md_and_reimport_bumps_version(db):
    s = svc.create_from_skill_md(db, SKILL_MD)
    assert s.name == "greeter" and s.version == 1 and s.source == "import"

    # 同名再导入 → 更新且版本 +1
    s2 = svc.create_from_skill_md(db, SKILL_MD.replace("说你好", "热情地说你好"))
    assert s2.id == s.id and s2.version == 2
    assert "热情" in s2.skill_md


def test_create_structured_and_conflict(db):
    s = svc.create_structured(
        db, {"name": "calc", "description": "算术", "kind": "instruction",
             "skill_md": "", "parameters_schema": None, "http_action": None}
    )
    assert s.source == "manual"
    with pytest.raises(SkillNameConflict):
        svc.create_structured(
            db, {"name": "calc", "description": "again", "kind": "instruction",
                 "skill_md": "", "parameters_schema": None, "http_action": None}
        )


def test_update_from_skill_md(db):
    s = svc.create_from_skill_md(db, SKILL_MD)
    updated = svc.update_from_skill_md(
        db, s.id, SKILL_MD.replace("description: 打招呼", "description: 改过了")
    )
    assert updated.description == "改过了" and updated.version == 2


def test_update_missing_returns_none(db):
    assert svc.update_from_skill_md(db, 9999, SKILL_MD) is None


def test_update_name_conflict(db):
    svc.create_from_skill_md(db, SKILL_MD)  # greeter
    other = svc.create_structured(
        db, {"name": "other", "description": "d", "kind": "instruction",
             "skill_md": "", "parameters_schema": None, "http_action": None}
    )
    with pytest.raises(SkillNameConflict):
        svc.update_from_skill_md(db, other.id, SKILL_MD)  # 想改名成 greeter


def test_bad_skill_md_raises(db):
    with pytest.raises(SkillParseError):
        svc.create_from_skill_md(db, "garbage")


def test_set_active_and_delete(db):
    s = svc.create_from_skill_md(db, SKILL_MD)
    svc.set_active(db, s.id, False)
    assert [x.name for x in svc.list_skills(db, active_only=True)] == []
    assert svc.delete_skill(db, s.id) is True
    assert svc.get_skill(db, s.id) is None
    assert svc.delete_skill(db, s.id) is False


def test_seed_builtins_idempotent(db):
    assert svc.seed_builtins(db) == 4   # wenyanwen, emoji-tldr, ip-geo, futures-trend
    assert svc.seed_builtins(db) == 0   # 幂等
    names = {s.name for s in svc.list_skills(db)}
    assert {"wenyanwen", "emoji-tldr", "ip-geo", "futures-trend"} <= names
    # ip-geo 默认停用
    ip = svc.get_by_name(db, "ip-geo")
    assert ip.is_active is False and ip.kind == "http"
