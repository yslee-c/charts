"""Agent 编排循环：渐进式披露 + Qwen tool calling。

产出一串事件字典（供上层转成 SSE）：
  {"delta": "..."}                         助手文本增量
  {"tool_call": {"skill","arguments"}}     模型决定调用某 skill
  {"tool_result": {"skill","ok"}}          该 skill 执行完毕
  {"error": "..."}                         出错
"""
import json
import logging
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.agent.llm import get_llm_client
from app.agent.llm.base import ChatMessage, ContentDelta, StreamEnd, ToolCallDelta
from app.agent.runner import SkillRunner
from app.services.skill_service import list_skills
from app.skills.registry import build_tools

logger = logging.getLogger("app.agent")

MAX_ROUNDS = 6  # 工具调用循环上限，防止无限调用


async def run_chat(
    db: Session, messages: list[ChatMessage], system_prompt: str
) -> AsyncIterator[dict]:
    tools, mapping = build_tools(list_skills(db, active_only=True))
    runner = SkillRunner(db)
    client = get_llm_client()

    convo: list[ChatMessage] = list(messages)
    if not convo or convo[0].get("role") != "system":
        convo.insert(0, {"role": "system", "content": system_prompt})

    for _ in range(MAX_ROUNDS):
        content_buf = ""
        tool_calls: dict[int, dict] = {}

        async for ev in client.stream(convo, tools=tools or None):
            if isinstance(ev, ContentDelta):
                content_buf += ev.text
                yield {"delta": ev.text}
            elif isinstance(ev, ToolCallDelta):
                slot = tool_calls.setdefault(
                    ev.index, {"id": None, "name": "", "args": ""}
                )
                if ev.id:
                    slot["id"] = ev.id
                if ev.name:
                    slot["name"] = ev.name
                if ev.arguments:
                    slot["args"] += ev.arguments
            elif isinstance(ev, StreamEnd):
                pass  # finish_reason 目前不需单独处理

        if not tool_calls:
            return  # 本轮是最终回答，已通过 delta 流出

        # 组装 assistant 的 tool_calls 消息
        tc_list = []
        for idx in sorted(tool_calls):
            slot = tool_calls[idx]
            tc_list.append(
                {
                    "id": slot["id"] or f"call_{idx}",
                    "type": "function",
                    "function": {
                        "name": slot["name"],
                        "arguments": slot["args"] or "{}",
                    },
                }
            )
        convo.append(
            {"role": "assistant", "content": content_buf or None, "tool_calls": tc_list}
        )

        # 逐个执行工具，把结果回灌
        for tc in tc_list:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
                if not isinstance(args, dict):
                    args = {}
            except json.JSONDecodeError:
                args = {}

            skill = mapping.get(name)
            yield {"tool_call": {"skill": name, "arguments": args}}

            if skill is None:
                result, ok = f"未找到 skill：{name}", False
            else:
                result = await runner.run(skill, args)
                ok = True

            # output 一并推给前端，用于「展开查看 skill 原始输出/可视化」
            yield {"tool_result": {"skill": name, "ok": ok, "output": result}}
            convo.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": result}
            )
        # 回到循环顶部，让模型基于工具结果继续

    yield {"error": f"已达最大工具调用轮数（{MAX_ROUNDS}），已停止。"}
