"""通义千问（Qwen）客户端 —— 走阿里云百炼 / DashScope 的 OpenAI 兼容模式。

参考：https://help.aliyun.com/zh/model-studio/developer-reference/compatibility-of-openai-with-dashscope
"""
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.agent.llm.base import ChatMessage, LLMClient
from app.core.config import settings


class QwenClient(LLMClient):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
        )
        self._model = settings.qwen_model

    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
