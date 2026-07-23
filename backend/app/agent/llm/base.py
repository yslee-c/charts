"""LLM 适配层抽象接口。

隔离各厂商差异，便于将来增减模型（当前实现：Qwen / 阿里云百炼）。

`stream()` 产出一串**归一化事件**，orchestrator 据此驱动对话循环，
不必关心各家 tool calling 的具体格式：
  - ContentDelta     文本增量
  - ToolCallDelta    工具调用的分片（流式下 name/arguments 会分多次到达）
  - StreamEnd        本轮结束（finish_reason: "stop" | "tool_calls" | ...）
"""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TypedDict


class ChatMessage(TypedDict, total=False):
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | None
    tool_calls: list  # assistant 发起的工具调用
    tool_call_id: str  # role=tool 时对应的调用 id


@dataclass
class ContentDelta:
    text: str


@dataclass
class ToolCallDelta:
    index: int
    id: str | None = None
    name: str | None = None
    arguments: str | None = None  # JSON 字符串分片，需按 index 累加


@dataclass
class StreamEnd:
    finish_reason: str | None = None


StreamEvent = ContentDelta | ToolCallDelta | StreamEnd


class LLMClient(ABC):
    @abstractmethod
    def stream(
        self, messages: list[ChatMessage], tools: list[dict] | None = None
    ) -> AsyncIterator[StreamEvent]:
        """带工具的流式对话，产出归一化事件。"""
        raise NotImplementedError
