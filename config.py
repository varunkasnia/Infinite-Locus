import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key-change-in-production")
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

    _db_url = os.environ.get("DATABASE_URL", "sqlite:///event_dashboard.db")

    if _db_url.startswith("postgres+asyncpg://") or _db_url.startswith("postgresql+asyncpg://"):
        _db_url = _db_url.replace("asyncpg://", "psycopg2://", 1)
    elif _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql+psycopg2://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_COOKIE_SAMESITE = "Lax"

    SOCKETIO_ASYNC_MODE = "eventlet"

    SCHEDULER_API_ENABLED = True

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024