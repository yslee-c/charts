"""会话相关 DTO。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class ConversationRename(BaseModel):
    title: str
