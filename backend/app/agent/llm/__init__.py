"""LLM 适配层：抽象接口 + 具体厂商实现（当前 Qwen）。"""
from app.agent.llm.base import ChatMessage, LLMClient
from app.agent.llm.qwen import QwenClient

__all__ = ["ChatMessage", "LLMClient", "QwenClient", "get_llm_client"]


def get_llm_client() -> LLMClient:
    """返回当前配置的 LLM 客户端。将来多厂商时在此按配置切换。"""
    return QwenClient()
