"""Skill 执行器。

- instruction 型：返回 SKILL.md 正文（渐进式披露 —— 把指令注入上下文，模型据此完成）。
- http 型：按 http_action 执行受控外部请求，返回响应文本。

每次执行都写一条 SkillRun 审计。
"""
import time

import httpx
from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.models.skill_run import SkillRun

_HTTP_TIMEOUT = 20.0
_MAX_OUTPUT = 4000  # 回灌给模型的结果长度上限，控成本


class SkillRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def run(self, skill: Skill, arguments: dict) -> str:
        start = time.perf_counter()
        status, error, output = "ok", None, ""
        try:
            if skill.kind == "http":
                output = await self._run_http(skill, arguments)
            else:
                # 渐进式披露：把完整指令交给模型
                output = skill.skill_md or skill.description
        except Exception as exc:  # noqa: BLE001
            status, error = "error", str(exc)
            output = f"调用 skill「{skill.name}」失败：{exc}"
        finally:
            self._audit(skill, arguments, output, status, error, start)
        return output

    async def _run_http(self, skill: Skill, arguments: dict) -> str:
        action = skill.http_action or {}
        method = str(action.get("method", "GET")).upper()
        url = str(action.get("url", ""))

        # 先用 {占位符} 填充 URL，剩余参数作为 query(GET) / json body(其它)
        remaining = dict(arguments)
        for key in list(remaining):
            token = "{" + key + "}"
            if token in url:
                url = url.replace(token, str(remaining.pop(key)))

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            if method == "GET":
                resp = await client.get(url, params=remaining)
            else:
                resp = await client.request(method, url, json=remaining)
        resp.raise_for_status()
        return resp.text[:_MAX_OUTPUT]

    def _audit(
        self,
        skill: Skill,
        arguments: dict,
        output: str,
        status: str,
        error: str | None,
        start: float,
    ) -> None:
        self.db.add(
            SkillRun(
                skill_id=skill.id,
                skill_name=skill.name,
                arguments=arguments,
                output=output[:8000],
                status=status,
                error=error,
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        )
        self.db.commit()
