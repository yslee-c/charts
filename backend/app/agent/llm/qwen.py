"""通义千问（Qwen）客户端 —— 走阿里云百炼 / DashScope 的 OpenAI 兼容模式。

参考：https://help.aliyun.com/zh/model-studio/developer-reference/compatibility-of-openai-with-dashscope
"""
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.agent.llm.base import (
    ChatMessage,
    ContentDelta,
    LLMClient,
    StreamEnd,
    StreamEvent,
    ToolCallDelta,
)
from app.core.config import settings


class QwenClient(LLMClient):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
        )
        self._model = settings.qwen_model

    async def stream(
        self, messages: list[ChatMessage], tools: list[dict] | None = None
    ) -> AsyncIterator[StreamEvent]:
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }
        if tools:  # 空列表不传，避免部分服务端报错
            kwargs["tools"] = tools

        stream = await self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta and delta.content:
                yield ContentDelta(text=delta.content)

            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    fn = tc.function
                    yield ToolCallDelta(
                        index=tc.index,
                        id=tc.id,
                        name=fn.name if fn else None,
                        arguments=fn.arguments if fn else None,
                    )

            if choice.finish_reason:
                yield StreamEnd(finish_reason=choice.finish_reason)
