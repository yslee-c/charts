"""聊天相关 DTO。"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """会话式对话：带上会话 id（无则新建），只传本轮新消息。"""

    conversation_id: int | None = None
    message: str = Field(min_length=1)
