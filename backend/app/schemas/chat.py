"""聊天相关 DTO。"""
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    # M1：无状态，对话历史由前端传入。M2 起接入会话持久化。
    messages: list[ChatMessage] = Field(min_length=1)
