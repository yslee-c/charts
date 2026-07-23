"""LLM 适配层抽象接口。

隔离各厂商差异，便于将来增减模型（当前实现：Qwen / 阿里云百炼）。
M2 会在此扩展 tool calling 相关接口。
"""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypedDict


class ChatMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient(ABC):
    @abstractmethod
    def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """流式对话：逐段产出文本增量（delta）。"""
        raise NotImplementedError
