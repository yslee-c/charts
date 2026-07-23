"""pytest 基建：临时 SQLite、每测试全新库、TestClient。

必须在导入任何 app 模块前设置环境变量，让 settings 读到测试配置。
"""
import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="charts-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db"
os.environ["DASHSCOPE_API_KEY"] = "test-key"  # 避免 chat 返回 503
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401  —— 注册所有模型到 Base.metadata
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture
def _db_setup():
    """每个测试用例前重建全部表，用完清空。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(_db_setup):
    """裸数据库会话（空库，不含内置 skill）—— 用于 service/单元测试。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(_db_setup):
    """API 测试客户端；进入 lifespan 会建表并植入内置 skill。"""
    with TestClient(fastapi_app) as c:
        yield c
