"""内置 skill 种子（Claude Skills 规范的 SKILL.md 文本）。

每项为 (SKILL.md 文本, 默认是否启用)。
- 两个 instruction 型：离线可用，用于演示「渐进式披露」。
- 一个 http 型：默认停用，作为对接外部 API 的模板（启用前请确认网络可达）。
"""

_WENYANWEN = """\
---
name: wenyanwen
description: 当用户想把白话文（现代中文）改写成文言文，或需要文言/古风的表达时使用。
---

# 文言文改写

当被调用时，请按以下要求把用户提供的现代中文改写成文言文：

1. 保持原意不变，力求简练、典雅。
2. 使用文言虚词（之、乎、者、也、矣、焉）与文言句式。
3. 避免生僻到难以理解的字词。
4. 先给出**文言文版本**，再附一行**白话回译**，方便对照。
"""

_EMOJI_TLDR = """\
---
name: emoji-tldr
description: 当用户要求用 emoji 精简总结一段内容、或想要「一句话 + emoji」的摘要时使用。
---

# Emoji 摘要

当被调用时：

1. 用 **3～5 条** bullet 概括核心要点，每条以一个贴切的 emoji 开头。
2. 最后附一行 **TL;DR**，不超过 20 字。
3. 语言与用户输入保持一致（中文输入则中文输出）。
"""

_IP_GEO = """\
---
name: ip-geo
description: 查询指定 IP 地址的地理位置信息（国家、地区、城市、运营商）。
kind: http
parameters:
  type: object
  properties:
    ip:
      type: string
      description: 要查询的 IP 地址，例如 8.8.8.8
  required:
    - ip
http_action:
  method: GET
  url: https://ipapi.co/{ip}/json/
---

# IP 归属查询

调用外部 API 查询 IP 的地理位置。把返回的国家、城市、运营商等信息，用简洁中文告诉用户。
"""

_FUTURES_TREND = """\
---
name: futures-trend
description: 当用户想分析某个期货品种的走势、判断趋势是否可能反转（123 法则 / 2B 法则）时使用。需要期货合约代码。
kind: native
parameters:
  type: object
  properties:
    symbol:
      type: string
      description: 期货合约代码，如 RB0（螺纹钢主力连续）、rb2410、V0、cu0
    bars:
      type: integer
      description: 分析最近多少根日K，默认 120（范围 30~500）
  required:
    - symbol
---

# 期货趋势分析（123 / 2B 法则）

被调用后你会收到一段结构化分析结果。请用简洁中文：
1. 说明该品种当前趋势方向、最近的摆动高/低点。
2. 说明 123 法则满足了哪几条（① 趋势线 ② 未创新高/低 ③ 破前低/前高），以及是否出现 2B 假突破。
3. 给出结论（可能见顶 / 见底 / 趋势延续 / 盘整）与参考止损位。
4. 结尾提醒：技术分析仅供参考，非投资建议，务必控制仓位与止损。
"""

# (SKILL.md, 默认是否启用)
BUILTIN_SKILLS: list[tuple[str, bool]] = [
    (_WENYANWEN, True),
    (_EMOJI_TLDR, True),
    (_IP_GEO, False),  # 模板：默认停用，启用前确认外网可达
    (_FUTURES_TREND, True),  # native：期货 123/2B 分析（需服务器装 akshare）
]

# 仅文本列表（供简单遍历）
BUILTIN_SKILL_MDS: list[str] = [md for md, _ in BUILTIN_SKILLS]
