"""应用配置：从环境变量 / .env 读取。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Skills Hub"
    # M0 用 SQLite；后续可改为 postgresql+psycopg://user:pass@host/db
    database_url: str = "sqlite:///./charts.db"

    # 阿里通义千问（百炼 / DashScope，OpenAI 兼容模式）—— M1 使用
    dashscope_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"

    frontend_origin: str = "http://localhost:3000"


settings = Settings()
