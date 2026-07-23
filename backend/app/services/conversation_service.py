"""会话领域服务。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def title_from(text: str, limit: int = 24) -> str:
    t = text.strip().replace("\n", " ")
    return t[:limit] + "…" if len(t) > limit else (t or "新对话")


def create(db: Session, title: str) -> Conversation:
    convo = Conversation(title=title)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def get(db: Session, conversation_id: int) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def list_all(db: Session) -> list[Conversation]:
    return list(
        db.scalars(select(Conversation).order_by(Conversation.updated_at.desc()))
    )


def messages(db: Session, conversation_id: int) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
    )


def add_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def touch(db: Session, conversation_id: int) -> None:
    convo = db.get(Conversation, conversation_id)
    if convo is not None:
        convo.updated_at = _utcnow()
        db.commit()


def rename(db: Session, conversation_id: int, title: str) -> Conversation | None:
    convo = db.get(Conversation, conversation_id)
    if convo is None:
        return None
    convo.title = title.strip() or convo.title
    db.commit()
    db.refresh(convo)
    return convo


def delete(db: Session, conversation_id: int) -> bool:
    convo = db.get(Conversation, conversation_id)
    if convo is None:
        return False
    db.delete(convo)
    db.commit()
    return True
