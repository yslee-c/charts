"""Skill 调用审计路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.skill import SkillRunOut
from app.services import skill_service as svc

router = APIRouter(prefix="/skill-runs", tags=["skill-runs"])


@router.get("", response_model=list[SkillRunOut])
def list_skill_runs(
    limit: int = 100, skill_id: int | None = None, db: Session = Depends(get_db)
):
    """最近的 skill 调用记录（倒序）。"""
    return svc.list_runs(db, limit=min(limit, 500), skill_id=skill_id)
