"""聊天路由：POST /api/chat，SSE 流式返回 Qwen 的回复。

M1：无状态、不带 skill，纯粹跑通流式对话。
SSE 事件格式：
  data: {"delta": "文本增量"}\n\n     —— 逐段推送
  data: {"error": "错误信息"}\n\n     —— 出错时
  data: [DONE]\n\n                     —— 流结束
"""
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIStatusError

from app.agent.llm import ChatMessage, get_llm_client
from app.core.config import settings
from app.schemas.chat import ChatRequest

logger = logging.getLogger("app.chat")

router = APIRouter(tags=["chat"])

DEFAULT_SYSTEM_PROMPT = (
    "你是 Skills 中心的 AI 助手。用简洁、友好的中文回答用户的问题。"
)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _format_error(exc: Exception) -> str:
    """把 LLM 服务的报错提取成清晰、可诊断的中文信息。"""
    if isinstance(exc, APIStatusError):
        provider_msg = ""
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            provider_msg = (
                body.get("message")
                or (body.get("error") or {}).get("message")
                or ""
            )
        detail = provider_msg or getattr(exc, "message", "") or str(exc)
        return f"模型服务返回 {exc.status_code}：{detail}（模型={settings.qwen_model}）"
    return str(exc)


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    if not settings.dashscope_api_key:
        raise HTTPException(
            status_code=503,
            detail="DASHSCOPE_API_KEY 未配置，请在 backend/.env 中设置后重启服务。",
        )

    messages: list[ChatMessage] = [
        {"role": m.role, "content": m.content} for m in req.messages
    ]
    # 若前端未提供 system 消息，则补一个默认人设
    if messages[0]["role"] != "system":
        messages.insert(0, {"role": "system", "content": DEFAULT_SYSTEM_PROMPT})

    client = get_llm_client()

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for delta in client.stream_chat(messages):
                yield _sse({"delta": delta})
        except Exception as exc:  # noqa: BLE001 —— 把错误透传给前端展示
            logger.exception("chat stream failed")
            yield _sse({"error": _format_error(exc)})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 关闭 Nginx 缓冲，保证实时
        },
    )
