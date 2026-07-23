# Skills 中心 —— 架构设计文档

> 状态：**草案 (Draft)** ｜ 最后更新：2026-07-23
>
> 本文档描述项目的整体构想与技术设计。当前仓库尚无代码，本文用于在动手编码前对齐设计。
> 文末「待确认事项」列出了需要产品/技术上拍板的开放问题。

---

## 1. 项目概述

一个 **Skills 中心（Skills Hub）**：用户在一个 agent 化的 AI 聊天窗口中提出需求，后端的 agent 根据对话内容**自主决定是否调用、调用哪些 skill** 来完成任务。同时，用户可以**编辑、导入、订阅** skill，构建属于自己的能力集合。

核心价值主张：
- **对话即入口**：主界面是一个聊天窗口，用户用自然语言表达需求，不需要手动选工具。
- **能力可组合**：skill 是可复用的能力单元，用户可自定义、从外部导入、订阅他人分享的 skill。
- **agent 自主编排**：agent 基于当前可用的 skill 集合和对话上下文，自己判断该不该用工具、用哪个、按什么顺序用。

### 关键概念：什么是「Skill」

一个 **skill** 是 agent 可以调用的一个能力单元。它至少包含：

| 字段 | 说明 |
| --- | --- |
| `name` / `slug` | 唯一标识 |
| `description` | 给 agent 看的自然语言描述（决定 agent 是否选用它，**至关重要**） |
| `input_schema` | 输入参数的 JSON Schema（用于 LLM 的 function/tool calling） |
| `implementation` | 实现方式：HTTP 调用外部 API / 执行一段脚本 / 调用内部服务 / 纯 prompt 模板 等 |
| `owner` / `visibility` | 归属与可见性（私有 / 公开 / 组织内） |
| `version` | 版本，支持编辑迭代 |

> Skill 的设计直接对标「LLM function calling / tool use」：`description` + `input_schema` 会被拼进给 LLM 的工具列表，LLM 决定调用哪个并给出参数，后端执行 `implementation` 并把结果回灌给 LLM。

---

## 2. 技术栈

| 层 | 选型 | 备注 |
| --- | --- | --- |
| 前端 | **Next.js**（App Router）+ TypeScript | 聊天窗口、skill 编辑/市场/订阅界面 |
| 后端 | **FastAPI**（Python）+ Pydantic | REST API + 流式聊天（SSE / WebSocket） |
| LLM | **Anthropic Claude**（默认，可替换） | 通过 tool use 实现 agent 编排 |
| 数据库 | PostgreSQL | skill、用户、会话、订阅关系 |
| ORM | SQLAlchemy 2.x + Alembic | 迁移管理 |
| 鉴权 | JWT / Session | 用户登录、skill 归属 |
| 异步任务 | （可选）Celery / RQ | skill 执行耗时较长时 |

> LLM 选型默认 Anthropic Claude，因其 tool use 能力成熟；实现上应做一层抽象，便于将来替换。

---

## 3. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                        前端 (Next.js)                          │
│                                                                │
│   ┌────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│   │ 聊天窗口    │   │ Skill 编辑器  │   │ Skill 市场 / 订阅   │  │
│   │ (主界面)    │   │              │   │                    │  │
│   └─────┬──────┘   └──────┬───────┘   └─────────┬──────────┘  │
└─────────┼─────────────────┼────────────────────┼─────────────┘
          │ SSE/WS (流式)    │ REST               │ REST
┌─────────┼─────────────────┼────────────────────┼─────────────┐
│         ▼                 ▼                    ▼               │
│                      后端 (FastAPI)                            │
│                                                                │
│   ┌─────────────────────────────────────────────────────┐    │
│   │              Agent 编排引擎 (Orchestrator)            │    │
│   │   对话循环：LLM ⇄ tool calls ⇄ skill 执行             │    │
│   └───────┬───────────────────────────┬────────────────-┘    │
│           │                           │                       │
│   ┌───────▼────────┐          ┌───────▼────────┐             │
│   │  LLM 适配层     │          │ Skill 注册/执行 │             │
│   │ (Claude 等)     │          │ (Registry+Runner)│            │
│   └────────────────┘          └───────┬────────┘             │
│                                       │                       │
│   ┌───────────────────────────────────▼──────────────────┐   │
│   │        领域服务：Skill / 订阅 / 会话 / 用户           │   │
│   └───────────────────────┬──────────────────────────────┘   │
└───────────────────────────┼──────────────────────────────────┘
                            ▼
                     PostgreSQL
```

### 建议的 Monorepo 目录结构

```
charts/
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── main.py             # 应用入口
│   │   ├── api/                # 路由 (chat, skills, subscriptions, auth)
│   │   ├── agent/              # ★ Agent 编排核心
│   │   │   ├── orchestrator.py # 对话循环
│   │   │   ├── llm/            # LLM 适配层 (claude.py, base.py)
│   │   │   └── runner.py       # skill 执行器
│   │   ├── skills/             # skill 注册、schema 构建、内置 skill
│   │   ├── models/             # SQLAlchemy 模型
│   │   ├── schemas/            # Pydantic DTO
│   │   ├── services/           # 领域服务
│   │   └── core/               # 配置、鉴权、依赖注入
│   ├── alembic/                # 数据库迁移
│   └── tests/
├── frontend/                   # Next.js
│   ├── app/                    # App Router 页面
│   │   ├── chat/               # 主聊天界面
│   │   ├── skills/             # skill 编辑 / 详情
│   │   └── marketplace/        # 市场 / 订阅
│   ├── components/
│   └── lib/                    # API client、SSE/WS 封装
├── docs/
│   └── DESIGN.md               # 本文档
└── docker-compose.yml          # 本地一键起 db + backend + frontend
```

---

## 4. 核心流程：Agent 如何决定调用 Skill

这是整个项目的心脏。一次用户消息的处理流程（对话循环）：

```
1. 用户在聊天窗口发送消息
        │
2. 后端加载「当前用户已订阅 + 自有」的 skill 集合
        │
3. 把这些 skill 转成 LLM 的 tools 列表（name + description + input_schema）
        │
4. 调用 LLM：传入 对话历史 + 用户消息 + tools
        │
5. LLM 返回：
        ├─(a) 直接文本回答 → 流式推给前端，结束
        └─(b) 一个或多个 tool_use（要调用某 skill + 参数）
                │
6. 后端用 Skill Runner 执行对应 skill，拿到结果
        │
7. 把 tool 结果回灌给 LLM，回到第 4 步（循环，直到 LLM 给出最终文本回答）
```

**要点：**
- 「调用或不调用 skill」完全由 LLM 在第 5 步自主判断 —— 这正是用户描述的「agent 根据对话决定调用与否」。
- skill 的 `description` 写得好不好，直接决定 agent 选得准不准。
- 需要设置**最大循环轮数**防止无限调用；需要考虑**并行 tool call**。
- 全程通过 **SSE 或 WebSocket** 把中间过程（正在思考、正在调用 XX skill、结果、最终回答）流式推给前端，提升体验。

---

## 5. 数据模型（初稿）

```
User        (id, email, password_hash, created_at, ...)

Skill       (id, slug, name, description, input_schema JSONB,
             implementation JSONB,          -- 类型 + 配置(url/脚本/模板...)
             owner_id → User, visibility,   -- private/public/org
             version, created_at, updated_at)

Subscription(id, user_id → User, skill_id → Skill, created_at)
             -- 用户订阅了哪些 skill（含他人公开的）

Conversation(id, user_id → User, title, created_at)

Message     (id, conversation_id → Conversation, role,   -- user/assistant/tool
             content JSONB,                 -- 文本 / tool_use / tool_result
             created_at)

SkillRun    (id, message_id, skill_id, input, output,    -- 执行审计
             status, latency_ms, created_at)
```

关系要点：
- **归属 vs 订阅**：`owner_id` 表示谁创建/能编辑；`Subscription` 表示谁把它加进了自己的可用集合。agent 在第 2 步加载的是「自有 ∪ 已订阅」。
- **导入**：从外部（文件 / URL / 其他用户）读入 skill 定义 → 校验 → 落库为当前用户的 `Skill`。
- **审计**：`SkillRun` 记录每次调用的输入输出，便于调试与观测。

---

## 6. API 设计（初稿）

| 方法 & 路径 | 说明 |
| --- | --- |
| `POST /api/chat` | 发送消息，返回 SSE/WS 流（agent 编排在此发生） |
| `GET /api/conversations` / `GET /api/conversations/{id}` | 会话列表 / 详情 |
| `GET/POST /api/skills` | 列出 / 创建 skill |
| `GET/PUT/DELETE /api/skills/{id}` | 查看 / 编辑 / 删除 skill |
| `POST /api/skills/import` | 导入 skill（文件 / URL） |
| `POST /api/skills/{id}/test` | 单独试跑一个 skill（调试用） |
| `POST /api/subscriptions` / `DELETE /api/subscriptions/{id}` | 订阅 / 取消订阅 |
| `GET /api/marketplace` | 浏览公开 skill |
| `POST /api/auth/login` / `register` | 鉴权 |

---

## 7. 关键技术挑战与注意点

1. **Skill 执行的安全性**：如果 skill 允许「执行脚本」，必须沙箱化（容器 / 子进程隔离 / 资源限制），否则是重大安全风险。建议 MVP 阶段先只支持「HTTP 调用外部 API」这种受控类型。
2. **Prompt / description 质量**：agent 选型准确度高度依赖 skill 描述。可考虑提供「描述编写助手」或校验。
3. **流式体验**：中间步骤（调用了哪个 skill）要实时可见，用户才信任 agent。
4. **循环与成本控制**：限制最大工具调用轮数、超时、token 预算。
5. **LLM 可替换性**：适配层要抽象干净，隔离各家 tool use 的格式差异。
6. **版本与兼容**：skill 被编辑后，正在进行的会话如何处理旧版本。

---

## 8. 分阶段落地建议

- **M0 脚手架**：monorepo、docker-compose、FastAPI hello + Next.js hello 打通。
- **M1 最小对话**：聊天窗口 + 后端接 LLM（不带 skill），跑通流式对话。
- **M2 Skill 内核**：Skill 数据模型 + 一两个内置 skill（如「HTTP 请求」）+ agent 编排循环，让 agent 真能调用工具。
- **M3 Skill 管理**：编辑器、导入、订阅、市场。
- **M4 打磨**：审计、安全沙箱、版本管理、成本控制。

---

## 9. 待确认事项（需要你拍板）

> 以下是我在写这份文档时做的**假设**，请逐条确认或修改：

1. **LLM 供应商**：默认用 Anthropic Claude（tool use 成熟）。是否有指定？是否需要多家可切换？
2. **Skill 的实现类型**：MVP 支持哪几种？（建议先只做「HTTP 调外部 API」+「prompt 模板」，暂不做任意脚本执行以规避安全风险）
3. **导入来源**：从哪导入？文件（JSON/YAML）、URL、还是要对接某个已有格式（比如 OpenAI plugin / MCP / Claude Skills 规范）？
4. **多租户/组织**：是纯个人使用，还是要支持团队/组织共享？
5. **部署形态**：本地开发用 docker-compose 就够，生产部署有目标平台吗？
6. **数据库**：确定 PostgreSQL 吗？还是想用更轻的（SQLite 起步）？
7. **市场是否社交化**：公开 skill 是否需要评分、收藏、作者主页等社区功能，还是先做纯列表？

---

*本文档是活文档，随设计推进持续更新。确认上述事项后，即可进入 M0 脚手架阶段。*
