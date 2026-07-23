"""把「已启用的 skill 集合」构造成 LLM 的 tools 列表（渐进式披露：只给 name+description）。"""
from app.models.skill import Skill

_EMPTY_SCHEMA = {"type": "object", "properties": {}}


def build_tools(skills: list[Skill]) -> tuple[list[dict], dict[str, Skill]]:
    """返回 (tools, name→skill 映射)。

    skill.name 已是合规 slug（小写字母/数字/连字符），可直接作为 function name。
    """
    tools: list[dict] = []
    mapping: dict[str, Skill] = {}
    for s in skills:
        params = s.parameters_schema or _EMPTY_SCHEMA
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": s.name,
                    "description": s.description,
                    "parameters": params,
                },
            }
        )
        mapping[s.name] = s
    return tools, mapping
