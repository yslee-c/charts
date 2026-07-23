"""测试用的假 LLM 客户端与 SSE 辅助。"""
import json

from app.agent.llm.base import ContentDelta, LLMClient, StreamEnd, ToolCallDelta


class EchoLLM(LLMClient):
    """回声：把最后一条 user 内容拼进回复，用于验证历史被正确加载。"""

    def __init__(self, prefix: str = "回复"):
        self.prefix = prefix

    async def stream(self, messages, tools=None):
        last_user = [m for m in messages if m.get("role") == "user"][-1]["content"]
        for ch in f"{self.prefix}[{last_user}]":
            yield ContentDelta(text=ch)
        yield StreamEnd(finish_reason="stop")


class ToolCallingLLM(LLMClient):
    """第一轮调用指定 skill，第二轮基于工具结果给最终回答。"""

    def __init__(self, skill_name: str, answer: str = "完成"):
        self.skill_name = skill_name
        self.answer = answer
        self.round = 0

    async def stream(self, messages, tools=None):
        self.round += 1
        if self.round == 1:
            yield ToolCallDelta(
                index=0, id="call_1", name=self.skill_name, arguments=""
            )
            yield ToolCallDelta(index=0, arguments="{}")
            yield StreamEnd(finish_reason="tool_calls")
        else:
            for ch in self.answer:
                yield ContentDelta(text=ch)
            yield StreamEnd(finish_reason="stop")


def drain_sse(resp) -> list[dict]:
    """把 SSE 流式响应解析成事件字典列表（跳过 [DONE]）。"""
    events: list[dict] = []
    for line in resp.iter_lines():
        if line.startswith("data:"):
            data = line[5:].strip()
            if data and data != "[DONE]":
                events.append(json.loads(data))
    return events
