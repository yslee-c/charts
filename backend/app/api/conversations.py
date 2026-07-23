"""会话管理路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.conversation import (
    ConversationDetail,
    ConversationOut,
    ConversationRename,
)
from app.services import conversation_service as svc

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    return svc.list_all(db)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    convo = svc.get(db, conversation_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return convo


@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: int, payload: ConversationRename, db: Session = Depends(get_db)
):
    convo = svc.rename(db, conversation_id, payload.title)
    if convo is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return convo


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    if not svc.delete(db, conversation_id):
        raise HTTPException(status_code=404, detail="会话不存在")
