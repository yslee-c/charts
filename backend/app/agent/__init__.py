"""Agent 编排核心（M1/M2 实现）。

- orchestrator.py：对话循环（渐进式披露 + Qwen tool calling）
- llm/：LLM 适配层（qwen.py 对接阿里云百炼 / DashScope）
- runner.py：skill 执行器（注入 SKILL.md 正文 + 受控 HTTP 动作）
"""
