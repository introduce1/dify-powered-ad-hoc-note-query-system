# -*- coding: utf-8 -*-
"""
统一配置管理 —— 支持通过环境变量覆盖默认值
使用方式：from config import Config
"""
import os


class Config:
    # ── 服务器 ──────────────────────────────────────────────────
    HOST: str = os.environ.get("APP_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("APP_PORT", 8888))
    DEBUG: bool = os.environ.get("APP_DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")

    # ── 数据库 ──────────────────────────────────────────────────
    DB_HOST: str = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.environ.get("DB_PORT", 3306))
    DB_USER: str = os.environ.get("DB_USER", "root")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_NAME: str = os.environ.get("DB_NAME", "record_db")
    DB_CHARSET: str = "utf8mb4"
    DB_CONNECT_TIMEOUT: int = 10

    @classmethod
    def get_db_config(cls) -> dict:
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "database": cls.DB_NAME,
            "charset": cls.DB_CHARSET,
            "connect_timeout": cls.DB_CONNECT_TIMEOUT,
            "cursorclass": None,  # 由 db.py 设置
        }

    # ── Dify 工作流 ─────────────────────────────────────────────
    DIFY_API_BASE: str = os.environ.get("DIFY_API_BASE", "http://localhost/v1")

    WORKFLOW_CONFIG: dict = {
        "suijisuicha": {
            "workflow_id": os.environ.get("WF_SUIJI_ID", ""),
            "api_key": os.environ.get("WF_SUIJI_KEY", ""),
            "base_url": f"{DIFY_API_BASE}/chat-messages",
            "app_type": "chatflow",  # 对话流
            "label": "随记随查",
            "description": "快速录入与检索碎片知识",
        },
        "duolunduihua": {
            "workflow_id": os.environ.get("WF_DUOLUN_ID", ""),
            "api_key": os.environ.get("WF_DUOLUN_KEY", ""),
            "base_url": f"{DIFY_API_BASE}/chat-messages",
            "app_type": "chatflow",  # 对话流
            "label": "多轮对话",
            "description": "自然语言多轮问答查询",
        },
        "shengchanjilu": {
            "workflow_id": os.environ.get("WF_SHENGCHAN_ID", ""),
            "api_key": os.environ.get("WF_SHENGCHAN_KEY", ""),
            "base_url": f"{DIFY_API_BASE}/workflows/run",
            "app_type": "workflow",  # 工作流
            "label": "生产记录",
            "description": "生产记录自然语言查询",
        },
    }

    # ── 流式传输 ────────────────────────────────────────────────
    STREAM_TIMEOUT: int = int(os.environ.get("STREAM_TIMEOUT", 300))
    STREAM_CHUNK_SIZE: int = 1024
    DEBUG_STREAM: bool = os.environ.get("DEBUG_STREAM", "1") == "1"

    # ── 分页 ────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ── CORS ────────────────────────────────────────────────────
    CORS_ORIGINS: list = ["*"]
