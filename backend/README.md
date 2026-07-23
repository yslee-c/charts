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
