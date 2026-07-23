"""native（内置）skill 的 handler 注册表。

native 型 skill 对应一个可信的 Python handler（一等公民，非用户上传脚本）。
handler 签名：`(arguments: dict) -> str`，返回值作为工具结果回灌给模型。

注意：各 handler 模块顶层**不要** import 重依赖（如 akshare），
放到函数内惰性导入，保证未安装时应用仍能启动。
"""
from collections.abc import Callable

from app.skills.native import futures_trend

NATIVE_HANDLERS: dict[str, Callable[[dict], str]] = {
    "futures-trend": futures_trend.run,
}


def get_handler(name: str) -> Callable[[dict], str] | None:
    return NATIVE_HANDLERS.get(name)
