# Skills 中心 —— 架构设计文档

> 状态：**设计确认中** ｜ 最后更新：2026-07-23
>
> 本文档描述项目的整体构想与技术设计，用于在动手编码前对齐设计。
> 关键技术选型已确认（见第 9 节「已确认决策」），据此即可进入 M0 脚手架阶段。

---

## 1. 项目概述

一个 **Skills 中心（Skills Hub）**：用户在一个 agent 化的 AI 聊天窗口中提出需求，后端的 agent 根据对话内容**自主决定是否调用、调用哪些 skill** 来完成任务。同时，用户可以**编辑、导入、订阅** skill，构建属于自己的能力集合。

核心价值主张：
- **对话即入口**：主界面是一个聊天窗口，用户用自然语言表达需求，不需要手动选工具。
- **能力可组合**：skill 是可复用的能力单元，用户可自定义、从外部导入、订阅他人分享的 skill。
- **agent 自主编排**：agent 基于当前可用的 skill 集合和对话上下文，自己判断该不该用工具、用哪个、按什么顺序用。

### 关键概念：什么是「Skill」

本项目的 skill **采用 [Claude Agent Skills 规范](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)**。一个 skill 是一个目录（可打包成 zip），核心是一个 `SKILL.md`：

```
my-skill/
├── SKILL.md          # ★ 必需：YAML frontmatter + Markdown 指令正文
├── scripts/          # 可选：附带脚本（MVP 不执行，见第 7 节安全说明）
├── references/       # 可选：参考资料
└── assets/           # 可选：模板、示例等
```

`SKILL.md` 的结构：

```markdown
---
name: my-skill                     # 唯一标识
description: 什么时候该用这个 skill  # ★ 决定 agent 是否选用它，至关重要
---

# 指令正文（Markdown）
当被调用时，agent 应遵循的具体步骤、约束、示例……
（本项目扩展：可在 frontmatter 声明受控的 HTTP 动作，供 skill 调用外部 API）
```

**渐进式披露（Progressive Disclosure）** 是这套规范的精髓，也是本项目落地的关键：
- **平时**：只把每个 skill 的 `name` + `description` 暴露给 LLM（开销极小）；
- **当 LLM 判断某 skill 相关时**：才把该 skill 的 `SKILL.md` 正文完整注入上下文，让模型按指令执行。

> **与 Qwen tool calling 的融合方式**（本项目核心机制）：把每个已订阅 skill 注册为 Qwen 的一个 tool（function name = skill `name`，function description = skill `description`）。Qwen 自主决定是否调用；一旦调用，后端把该 skill 的 `SKILL.md` 正文（及其声明的 HTTP 动作结果）作为 tool 结果回灌给 Qwen，模型据此继续完成任务。这样既 100% 兼容 Claude Skills 导入格式，又让 Qwen 来做「调不调用」的决策。

---

## 2. 技术栈

| 层 | 选型 | 备注 |
| --- | --- | --- |
| 前端 | **Next.js**（App Router）+ TypeScript | 聊天窗口、skill 编辑/市场/订阅界面 |
| 后端 | **FastAPI**（Python）+ Pydantic | REST API + 流式聊天（SSE / WebSocket） |
| LLM | **阿里通义千问 Qwen**（阿里云百炼 / DashScope） | 通过 tool calling 实现 agent 编排；面向中国境内业务合规部署 |
| 数据库 | **SQLite 起步 → 后续迁移 PostgreSQL** | 用 SQLAlchemy 抽象，尽量少写数据库特定语法以便平滑切换 |
| ORM | SQLAlchemy 2.x + Alembic | 迁移管理；从一开始就用 Alembic，换库时省事 |
| 鉴权 | 单用户，MVP 从简 | 个人使用，暂不做注册/多账号（见第 5 节） |
| 异步任务 | （可选，后置）Celery / RQ | skill 执行耗时较长时再引入 |

> **LLM = 通义千问**：考虑到后续要在中国境内开展业务，选用阿里云的 Qwen 系列（如 `qwen-max` / `qwen-plus`），走阿里云百炼（DashScope）接口，支持 function/tool calling。实现上仍做一层 **LLM 适配抽象**，隔离厂商差异、便于将来增减模型。DashScope 提供 OpenAI 兼容模式，可优先用它降低接入成本。
>
> **数据库 = SQLite 起步**：本地开发与早期上线用 SQLite（零运维、单文件），业务量上来后迁移 PostgreSQL。**注意**：JSON 字段用 SQLAlchemy 的通用 `JSON` 类型（而非 PG 专属 `JSONB`），避免绑定；迁移时主要关注并发写、JSON 查询、全文检索等差异。

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
│   │ (Qwen / 百炼)   │          │ (Registry+Runner)│            │
│   └────────────────┘          └───────┬────────┘             │
│                                       │                       │
│   ┌───────────────────────────────────▼──────────────────┐   │
│   │        领域服务：Skill / 订阅 / 会话                  │   │
│   └───────────────────────┬──────────────────────────────┘   │
└───────────────────────────┼──────────────────────────────────┘
                            ▼
              SQLite（起步）→ PostgreSQL（后续）
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
│   │   │   ├── llm/            # LLM 适配层 (qwen.py, base.py)
│   │   │   └── runner.py       # skill 执行器
│   │   ├── skills/             # SKILL.md 解析、tool schema 构建、内置 skill
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

采用 **渐进式披露 + Qwen tool calling** 的融合机制（见第 1 节）：

```
1. 用户在聊天窗口发送消息
        │
2. 后端加载「当前已订阅 + 自有」的 skill 集合
        │
3. 只用每个 skill 的 name + description 构造 Qwen 的 tools 列表
   （此时不注入 SKILL.md 正文 —— 渐进式披露，省 token）
        │
4. 调用 Qwen：传入 对话历史 + 用户消息 + tools
        │
5. Qwen 返回：
        ├─(a) 直接文本回答 → 流式推给前端，结束
        └─(b) 一个或多个 tool_call（要用某 skill）
                │
6. Skill Runner 处理该 skill：
     - 把 SKILL.md 正文指令注入上下文；
     - 若该 skill 声明了 HTTP 动作，则执行受控的外部 API 调用；
     - 汇总为 tool 结果
        │
7. 把 tool 结果回灌给 Qwen，回到第 4 步（循环，直到给出最终文本回答）
```

**要点：**
- 「调用或不调用 skill」完全由 Qwen 在第 5 步自主判断 —— 这正是你要的「agent 根据对话决定调用与否」。
- skill 的 `description`（即 `SKILL.md` frontmatter）写得好不好，直接决定 agent 选得准不准。
- **渐进式披露**：第 3 步只给 name+description，第 6 步才展开完整正文，skill 多了也不爆 token。
- 需要设置**最大循环轮数**防止无限调用；需要考虑**并行 tool call**。
- 全程通过 **SSE 或 WebSocket** 把中间过程（正在思考、正在调用 XX skill、结果、最终回答）流式推给前端，提升体验。

---

## 5. 数据模型（初稿）

> 说明：**个人单用户**版本，MVP **不做注册/多账号**，因此没有 `User` 表；将来要多租户时再引入 `User` 并在各表加 `user_id` 外键。JSON 字段统一用 SQLAlchemy 通用 `JSON` 类型（不用 PG 专属 `JSONB`），便于 SQLite→PostgreSQL 迁移。

```
Skill       (id, name, description,             -- name/description 来自 SKILL.md frontmatter
             skill_md TEXT,                     -- SKILL.md 正文（渐进披露时注入）
             http_actions JSON,                 -- 本项目扩展：声明的受控 HTTP 动作
             bundle_path TEXT,                   -- 附带 scripts/references/assets 的存放位置
             source,                            -- 来源：manual / import
             is_active BOOL,                    -- 是否在当前可用集合（即“订阅”）
             version, created_at, updated_at)

Conversation(id, title, created_at)

Message     (id, conversation_id → Conversation, role,   -- user/assistant/tool
             content JSON,                  -- 文本 / tool_call / tool_result
             created_at)

SkillRun    (id, message_id, skill_id, input, output,    -- 执行审计
             status, latency_ms, created_at)
```

关系要点：
- **订阅 = `is_active`**：单用户下，「订阅/取消订阅」简化为把某个 skill 标记为是否加入当前可用集合。agent 在第 2 步加载的就是 `is_active = true` 的 skill。（多租户化时再拆出独立的 `Subscription` 表。）
- **导入**：读入一个 Claude Skills 包（含 `SKILL.md` 的目录 / zip）→ 解析 frontmatter 与正文 → 校验 → 落库为 `Skill`（`source = import`）。
- **审计**：`SkillRun` 记录每次调用的输入输出，便于调试与观测。

---

## 6. API 设计（初稿）

| 方法 & 路径 | 说明 |
| --- | --- |
| `POST /api/chat` | 发送消息，返回 SSE/WS 流（agent 编排在此发生） |
| `GET /api/conversations` / `GET /api/conversations/{id}` | 会话列表 / 详情 |
| `GET/POST /api/skills` | 列出 / 创建 skill |
| `GET/PUT/DELETE /api/skills/{id}` | 查看 / 编辑 / 删除 skill |
| `POST /api/skills/import` | 导入 Claude Skills 包（上传 zip / 目录） |
| `POST /api/skills/{id}/test` | 单独试跑一个 skill（调试用） |
| `POST /api/skills/{id}/activate` / `deactivate` | 加入 / 移出当前可用集合（即“订阅”，单用户下即 `is_active` 开关） |

> 单用户 MVP 暂不做 `auth` 与 `marketplace`（社交化市场）；将来多租户时再补。

---

## 7. 关键技术挑战与注意点

1. **Skill 执行的安全性**：Claude Skills 包可以附带 `scripts/` 可执行脚本，但 **MVP 一律不执行**这些脚本 —— 只把 `SKILL.md` 正文当作指令（prompt 模板），外加 skill 显式声明的**受控 HTTP 动作**。将来要执行脚本，必须先做沙箱化（容器 / 子进程隔离 / 资源限制）。
2. **Prompt / description 质量**：agent 选型准确度高度依赖 `SKILL.md` 的 `description`。可考虑提供「描述编写助手」或校验。
3. **流式体验**：中间步骤（调用了哪个 skill）要实时可见，用户才信任 agent。
4. **循环与成本控制**：限制最大工具调用轮数、超时、token 预算。
5. **LLM 可替换性**：适配层抽象干净，当前对接 Qwen（百炼/DashScope），隔离厂商 tool calling 格式差异。
6. **SQLite→PostgreSQL 迁移**：坚持用 SQLAlchemy 通用类型、Alembic 管迁移，避免 SQLite/PG 专属语法；注意两者在并发写、JSON 查询、全文检索上的差异。
7. **版本与兼容**：skill 被编辑后，正在进行的会话如何处理旧版本。

---

## 8. 分阶段落地建议

- **M0 脚手架**：monorepo、docker-compose、FastAPI hello + Next.js hello 打通；SQLite + Alembic 初始化。
- **M1 最小对话**：聊天窗口 + 后端接 **Qwen**（不带 skill），跑通流式对话。
- **M2 Skill 内核**：Skill 数据模型 + `SKILL.md` 解析 + 一两个内置 skill + agent 编排循环（渐进披露 + tool calling），让 agent 真能调用 skill。
- **M3 Skill 管理**：编辑器、导入 Claude Skills 包、启用/停用（订阅）。
- **M4 打磨**：审计、脚本沙箱、版本管理、成本控制；（视业务）迁移 PostgreSQL。

---

## 9. 已确认决策

| # | 事项 | 决策 |
| --- | --- | --- |
| 1 | **LLM 供应商** | **阿里通义千问 Qwen**（阿里云百炼 / DashScope），面向中国境内业务；保留 LLM 适配层便于将来增减 |
| 2 | **Skill 实现类型** | **HTTP 调外部 API + prompt 模板（SKILL.md 指令）**；MVP 不执行附带脚本 |
| 3 | **导入格式** | **Claude Agent Skills 规范**（`SKILL.md` + frontmatter + 可选 scripts/references/assets） |
| 4 | **数据库** | **SQLite 起步，后续迁移 PostgreSQL**；用 SQLAlchemy 通用类型 + Alembic 保持可移植 |
| 5 | **使用形态** | **个人单用户**；MVP 不做注册/多账号/社交化市场，将来再多租户化 |

### 仍可后续再定（不阻塞 M0）
- **部署形态**：生产部署的目标平台（阿里云 ECS / 容器服务 等）。
- **具体 Qwen 型号**：`qwen-max` / `qwen-plus` / `qwen-turbo` 的取舍（按效果与成本权衡，可运行时配置）。

---

*本文档是活文档，随设计推进持续更新。以上决策已确认，可进入 M0 脚手架阶段。*
