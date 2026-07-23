"""Skill 领域服务：增删查、导入、启停、内置种子。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.skills.builtins import BUILTIN_SKILLS
from app.skills.parser import SkillParseError, parse_skill_md


def list_skills(db: Session, active_only: bool = False) -> list[Skill]:
    stmt = select(Skill).order_by(Skill.name)
    if active_only:
        stmt = stmt.where(Skill.is_active.is_(True))
    return list(db.scalars(stmt))


def get_skill(db: Session, skill_id: int) -> Skill | None:
    return db.get(Skill, skill_id)


def get_by_name(db: Session, name: str) -> Skill | None:
    return db.scalar(select(Skill).where(Skill.name == name))


def create_from_skill_md(
    db: Session, text: str, source: str = "import"
) -> Skill:
    """解析一段 SKILL.md 文本并落库；同名则更新（版本+1）。"""
    fields = parse_skill_md(text)  # 可能抛 SkillParseError
    existing = get_by_name(db, fields["name"])
    if existing is not None:
        existing.description = fields["description"]
        existing.skill_md = fields["skill_md"]
        existing.kind = fields["kind"]
        existing.parameters_schema = fields["parameters_schema"]
        existing.http_action = fields["http_action"]
        existing.version += 1
        db.commit()
        db.refresh(existing)
        return existing

    skill = Skill(source=source, is_active=True, **fields)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


class SkillNameConflict(ValueError):
    """新名称与另一个已存在的 skill 冲突。"""


def update_from_skill_md(db: Session, skill_id: int, text: str) -> Skill | None:
    """按 id 用一段 SKILL.md 更新 skill（版本 +1）。

    - 返回 None 表示 skill 不存在；
    - 解析失败抛 SkillParseError；
    - 新名称与其他 skill 冲突抛 SkillNameConflict。
    """
    skill = db.get(Skill, skill_id)
    if skill is None:
        return None

    fields = parse_skill_md(text)  # 可能抛 SkillParseError
    other = get_by_name(db, fields["name"])
    if other is not None and other.id != skill_id:
        raise SkillNameConflict(f"已存在同名 skill：{fields['name']}")

    for key, value in fields.items():
        setattr(skill, key, value)
    skill.version += 1
    db.commit()
    db.refresh(skill)
    return skill


def set_active(db: Session, skill_id: int, is_active: bool) -> Skill | None:
    skill = db.get(Skill, skill_id)
    if skill is None:
        return None
    skill.is_active = is_active
    db.commit()
    db.refresh(skill)
    return skill


def delete_skill(db: Session, skill_id: int) -> bool:
    skill = db.get(Skill, skill_id)
    if skill is None:
        return False
    db.delete(skill)
    db.commit()
    return True


def seed_builtins(db: Session) -> int:
    """插入内置 skill（幂等：已存在同名则跳过）。返回新增数量。"""
    added = 0
    for text, active in BUILTIN_SKILLS:
        try:
            fields = parse_skill_md(text)
        except SkillParseError:
            continue
        if get_by_name(db, fields["name"]) is not None:
            continue
        db.add(Skill(source="builtin", is_active=active, **fields))
        added += 1
    if added:
        db.commit()
    return added
