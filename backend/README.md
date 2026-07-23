# Backend — Skills Hub (FastAPI)

FastAPI + SQLAlchemy + Alembic + SQLite。

## 快速开始

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # 按需修改

# （M2 有模型后）初始化/升级数据库：
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

- 健康检查：http://localhost:8000/api/health
- 交互式 API 文档：http://localhost:8000/docs

> 首次启动会自动建表并植入内置 skill（`wenyanwen`、`emoji-tldr` 默认启用，
> `ip-geo` 为 http 模板、默认停用）。配好 `DASHSCOPE_API_KEY` 后即可在
> http://localhost:8000/docs 或前端聊天页体验 agent 自主调用 skill。

## 主要接口

| 方法 & 路径 | 说明 |
| --- | --- |
| `POST /api/chat` | SSE 流式对话（body: `{conversation_id?, message}`）；无 id 则新建会话，服务端加载历史、落库消息、agent 按需调用 skill |
| `GET /api/conversations` | 会话列表（按更新时间倒序） |
| `GET /api/conversations/{id}` | 会话详情（含消息） |
| `PATCH /api/conversations/{id}` | 重命名会话 |
| `DELETE /api/conversations/{id}` | 删除会话（级联删除消息） |
| `GET /api/skills?active_only=` | 列出 skill |
| `POST /api/skills/import` | 导入一段 SKILL.md（Claude Skills 规范），同名则更新并 +1 版本 |
| `PATCH /api/skills/{id}/active` | 启用 / 停用（即“订阅”开关） |
| `DELETE /api/skills/{id}` | 删除 skill |

## 目录

```
app/
├── main.py        # 应用入口
├── api/           # 路由（当前：health）
├── core/          # 配置、数据库
├── agent/         # Agent 编排（M1/M2）
├── skills/        # Skill 子系统（M2）
├── models/        # ORM 模型（M2）
├── schemas/       # Pydantic DTO
└── services/      # 领域服务
alembic/           # 数据库迁移
```

## 数据库迁移（Alembic）

数据库 URL 由 `app/core/config.py` 的 `DATABASE_URL` 决定（默认 SQLite）。
新增/修改模型后生成迁移：

```bash
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

> 为便于将来 SQLite → PostgreSQL 迁移：只用 SQLAlchemy 通用类型（如 `JSON`，
> 不用 PG 专属 `JSONB`），env.py 已开启 `render_as_batch` 以支持 SQLite 的 ALTER。
