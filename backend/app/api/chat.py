"""聊天路由：POST /api/chat，SSE 流式返回 agent 的回复，并持久化会话。

请求：{ conversation_id?: int, message: str }。无 conversation_id 则新建会话。
服务端从库加载历史、跑 agent 编排、把用户与助手消息落库。

SSE 事件：
  data: {"conversation": {"id": 1, "title": "...", "is_new": true}}\n\n   —— 首帧
  data: {"delta": "文本增量"}\n\n
  data: {"tool_call": {"skill": "...", "arguments": {...}}}\n\n
  data: {"tool_result": {"skill": "...", "ok": true}}\n\n
  data: {"error": "错误信息"}\n\n
  data: [DONE]\n\n
"""
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIStatusError
from sqlalchemy.orm import Session

from app.agent.llm.base import ChatMessage
from app.agent.orchestrator import run_chat
from app.core.config import settings
from app.core.db import get_db
from app.schemas.chat import ChatRequest
from app.services import conversation_service as conv_svc

logger = logging.getLogger("app.chat")

router = APIRouter(tags=["chat"])

DEFAULT_SYSTEM_PROMPT = (
    "你是 Skills 中心的 AI 助手。用简洁、友好的中文回答用户的问题。"
    "当某个 skill 能更好地完成用户的需求时，主动调用它。"
)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _format_error(exc: Exception) -> str:
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
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    if not settings.dashscope_api_key:
        raise HTTPException(
            status_code=503,
            detail="DASHSCOPE_API_KEY 未配置，请在 backend/.env 中设置后重启服务。",
        )

    # 载入或新建会话
    if req.conversation_id is not None:
        convo = conv_svc.get(db, req.conversation_id)
        if convo is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        is_new = False
    else:
        convo = conv_svc.create(db, title=conv_svc.title_from(req.message))
        is_new = True

    conv_id, conv_title = convo.id, convo.title

    # 落库用户消息，并据此构建给模型的历史
    conv_svc.add_message(db, conv_id, "user", req.message)
    history: list[ChatMessage] = [
        {"role": m.role, "content": m.content} for m in conv_svc.messages(db, conv_id)
    ]

    async def event_stream() -> AsyncIterator[str]:
        yield _sse(
            {"conversation": {"id": conv_id, "title": conv_title, "is_new": is_new}}
        )
        assistant_text = ""
        try:
            async for event in run_chat(db, history, DEFAULT_SYSTEM_PROMPT):
                if "delta" in event:
                    assistant_text += event["delta"]
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat stream failed")
            yield _sse({"error": _format_error(exc)})
        finally:
            # 持久化助手回复（含被中途停止时的部分内容）
            if assistant_text.strip():
                try:
                    conv_svc.add_message(db, conv_id, "assistant", assistant_text)
                    conv_svc.touch(db, conv_id)
                except Exception:  # noqa: BLE001
                    logger.exception("persist assistant message failed")
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
