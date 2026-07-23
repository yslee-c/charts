"""Skill 管理路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.skill import SkillActive, SkillImport, SkillOut
from app.services import skill_service as svc
from app.services.skill_service import SkillNameConflict
from app.skills.parser import SkillParseError, render_skill_md

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
def list_skills(active_only: bool = False, db: Session = Depends(get_db)):
    return svc.list_skills(db, active_only=active_only)


@router.get("/{skill_id}", response_model=SkillOut)
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = svc.get_skill(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill 不存在")
    return skill


@router.get("/{skill_id}/source")
def get_skill_source(skill_id: int, db: Session = Depends(get_db)) -> dict:
    """返回可编辑的 SKILL.md 文本（由结构化字段重建）。"""
    skill = svc.get_skill(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill 不存在")
    return {"content": render_skill_md(skill)}


@router.post("/import", response_model=SkillOut, status_code=201)
def import_skill(payload: SkillImport, db: Session = Depends(get_db)):
    """导入一段 SKILL.md 文本（Claude Skills 规范）；同名则更新。"""
    try:
        return svc.create_from_skill_md(db, payload.content, source="import")
    except SkillParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/{skill_id}", response_model=SkillOut)
def update_skill(skill_id: int, payload: SkillImport, db: Session = Depends(get_db)):
    """用一段 SKILL.md 更新指定 skill（版本 +1）。"""
    try:
        skill = svc.update_from_skill_md(db, skill_id, payload.content)
    except SkillParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SkillNameConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if skill is None:
        raise HTTPException(status_code=404, detail="skill 不存在")
    return skill


@router.patch("/{skill_id}/active", response_model=SkillOut)
def set_active(skill_id: int, payload: SkillActive, db: Session = Depends(get_db)):
    """启用 / 停用（单用户下即“订阅”开关）。"""
    skill = svc.set_active(db, skill_id, payload.is_active)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill 不存在")
    return skill


@router.delete("/{skill_id}", status_code=204)
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    if not svc.delete_skill(db, skill_id):
        raise HTTPException(status_code=404, detail="skill 不存在")
