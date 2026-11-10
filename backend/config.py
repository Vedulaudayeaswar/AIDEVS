"""Central configuration for the AIDevs platform.

Every setting comes from environment variables so the same code runs locally,
in tests and on Render. Secrets are never given insecure production defaults.
"""
import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _database_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///" + os.path.join(BASE_DIR, "instance", "aidevs.db")
    # Render / Heroku style URLs use the deprecated "postgres://" scheme.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    ENV = os.getenv("FLASK_ENV", "development")
    IS_PRODUCTION = ENV == "production"
    TESTING = False

    SQLALCHEMY_DATABASE_URI = _database_url()
    AUTO_MIGRATE = _bool("AUTO_MIGRATE", True)

    # --- Auth -------------------------------------------------------------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or ""
    ACCESS_TOKEN_MINUTES = _int("ACCESS_TOKEN_MINUTES", 15)
    REFRESH_TOKEN_DAYS = _int("REFRESH_TOKEN_DAYS", 30)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=ACCESS_TOKEN_MINUTES)

    # --- CORS -------------------------------------------------------------
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,https://aidevs-frontend.onrender.com",
        ).split(",")
        if o.strip()
    ]

    # --- AI (single platform-owned Groq key) -------------------------------
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    AI_TIMEOUT_SECONDS = _int("AI_TIMEOUT_SECONDS", 90)
    AI_MAX_RETRIES = _int("AI_MAX_RETRIES", 3)
    AI_DAILY_REQUESTS_PER_USER = _int("AI_DAILY_REQUESTS_PER_USER", 150)
    AI_DAILY_TOKENS_PER_USER = _int("AI_DAILY_TOKENS_PER_USER", 600_000)
    AI_MAX_CONCURRENT_JOBS = _int("AI_MAX_CONCURRENT_JOBS", 2)

    # --- Uploads / crawler ------------------------------------------------
    MAX_ASSET_BYTES = _int("MAX_ASSET_BYTES", 3 * 1024 * 1024)
    MAX_CONTENT_LENGTH = _int("MAX_REQUEST_BYTES", 6 * 1024 * 1024)
    CRAWLER_MAX_PAGES = _int("CRAWLER_MAX_PAGES", 5)
    CRAWLER_TIMEOUT_SECONDS = _int("CRAWLER_TIMEOUT_SECONDS", 10)
    CRAWLER_USER_AGENT = "AIDevsBot/2.0 (+https://github.com/Vedulaudayeaswar/AIDevs)"

    # Public base URL of this API (used for asset URLs inside previews/exports)
    PUBLIC_API_URL = os.getenv("PUBLIC_API_URL") or os.getenv("RENDER_EXTERNAL_URL") or ""

    @classmethod
    def validate(cls):
        """Fail fast on dangerous production configuration."""
        if not cls.JWT_SECRET_KEY:
            if cls.IS_PRODUCTION:
                raise RuntimeError("JWT_SECRET_KEY must be set in production")
            # Development only: random per-process secret (sessions reset on restart).
            cls.JWT_SECRET_KEY = secrets.token_urlsafe(48)
            print("WARNING: JWT_SECRET_KEY not set - using a random development secret.")
        if cls.IS_PRODUCTION and len(cls.JWT_SECRET_KEY) < 32:
            raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters")
        if cls.IS_PRODUCTION and cls.SQLALCHEMY_DATABASE_URI.startswith("sqlite") and                 os.getenv("ALLOW_SQLITE_IN_PRODUCTION") != "1":
            # Render's filesystem is ephemeral: a SQLite file would silently lose every user on restart.
            raise RuntimeError("Production requires DATABASE_URL to point at PostgreSQL (e.g. Neon free plan). "
                               "Refusing to start with SQLite.")


class TestConfig(Config):
    TESTING = True
    ENV = "testing"
    IS_PRODUCTION = False
    # In-memory SQLite by default; CI also runs the suite on PostgreSQL via TEST_DATABASE_URL.
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL") or "sqlite://"
    JWT_SECRET_KEY = "test-secret-key-that-is-long-enough-1234567890"  # noqa: S105  (test-only secret)
    AUTO_MIGRATE = False
    AI_DAILY_REQUESTS_PER_USER = 1000
