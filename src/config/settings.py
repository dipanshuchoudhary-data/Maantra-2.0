
"""
Application configuration loader for Maantra.

Loads environment variables from `.env`, validates them,
and exposes a strongly-typed settings object.

This replaces the TypeScript configuration system that used:
- dotenv
- zod
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


# ------------------------------------------------
# Helper
# ------------------------------------------------

def parse_array(value: Optional[str]) -> List[str]:
    if not value:
        return ["*"]
    return [v.strip() for v in value.split(",")]


# ------------------------------------------------
# Configuration Models
# ------------------------------------------------


class SlackConfig(BaseModel):
    bot_token: str
    signing_secret: Optional[str] = None
    app_token: Optional[str] = None
    user_token: Optional[str] = None


class AIConfig(BaseModel):
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    default_model: str = "gpt-4o"


class RAGConfig(BaseModel):
    enabled: bool = True
    embedding_provider: str = "openai"  # openai, cohere, openrouter, gemini
    embedding_model: str = "text-embedding-3-small"  # or embed-english-v3.0 for cohere
    embedding_dimensions: int = 1536
    vector_db_path: str = "./data/chroma"
    index_interval_hours: int = 1
    max_results: int = 10
    min_similarity: float = 0.5


class MemoryConfig(BaseModel):
    enabled: bool = True
    extraction_model: str = "gpt-4o-mini"


class AppConfig(BaseModel):
    log_level: str = "info"
    database_path: str = "./data/assistant.db"
    max_history_messages: int = 50
    session_timeout_minutes: int = 60


class SecurityConfig(BaseModel):
    dm_policy: str = "pairing"
    allowed_users: List[str] = Field(default_factory=lambda: ["*"])
    allowed_channels: List[str] = Field(default_factory=lambda: ["*"])


class FeatureFlags(BaseModel):
    thread_summary: bool = True
    task_scheduler: bool = True
    reactions: bool = True
    typing_indicator: bool = True


# ------------------------------------------------
# Main Settings Object
# ------------------------------------------------


class Settings(BaseModel):

    slack: SlackConfig
    ai: AIConfig
    rag: RAGConfig
    memory: MemoryConfig
    app: AppConfig
    security: SecurityConfig
    features: FeatureFlags

    rag_enabled: bool
    memory_enabled: bool

    slack_bot_token: str
    slack_app_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    slack_port: int = 3000

    dm_policy: str


# ------------------------------------------------
# Load Settings
# ------------------------------------------------


def load_settings() -> Settings:

    slack = SlackConfig(
        bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
        app_token=os.getenv("SLACK_APP_TOKEN"),
        user_token=os.getenv("SLACK_USER_TOKEN"),
    )

    ai = AIConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        cohere_api_key=os.getenv("COHERE_API_KEY"),
        default_model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
    )

    rag = RAGConfig(
        enabled=os.getenv("RAG_ENABLED", "true") != "false",
        embedding_provider=os.getenv(
            "RAG_EMBEDDING_PROVIDER",
            os.getenv("EMBEDDING_PROVIDER", "openai"),
        ).lower(),
        embedding_model=os.getenv(
            "RAG_EMBEDDING_MODEL",
            os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        ),
        embedding_dimensions=int(
            os.getenv("RAG_EMBEDDING_DIMENSIONS",
                      os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        ),
        vector_db_path=os.getenv(
            "RAG_VECTOR_DB_PATH",
            "./data/chroma",
        ),
        index_interval_hours=int(
            os.getenv("RAG_INDEX_INTERVAL_HOURS", "1")
        ),
        max_results=int(os.getenv("RAG_MAX_RESULTS", "10")),
        min_similarity=float(os.getenv("RAG_MIN_SIMILARITY", "0.5")),
    )

    memory = MemoryConfig(
        enabled=os.getenv("MEMORY_ENABLED", "true") != "false",
        extraction_model=os.getenv(
            "MEMORY_EXTRACTION_MODEL",
            "gpt-4o-mini",
        ),
    )

    app = AppConfig(
        log_level=os.getenv("LOG_LEVEL", "info"),
        database_path=os.getenv(
            "DATABASE_PATH",
            "./data/assistant.db",
        ),
        max_history_messages=int(
            os.getenv("MAX_HISTORY_MESSAGES", "50")
        ),
        session_timeout_minutes=int(
            os.getenv("SESSION_TIMEOUT_MINUTES", "60")
        ),
    )

    security = SecurityConfig(
        dm_policy=os.getenv("DM_POLICY", "pairing"),
        allowed_users=parse_array(os.getenv("ALLOWED_USERS")),
        allowed_channels=parse_array(os.getenv("ALLOWED_CHANNELS")),
    )

    features = FeatureFlags(
        thread_summary=os.getenv(
            "ENABLE_THREAD_SUMMARY", "true"
        )
        != "false",
        task_scheduler=os.getenv(
            "ENABLE_TASK_SCHEDULER", "true"
        )
        != "false",
        reactions=os.getenv(
            "ENABLE_REACTIONS", "true"
        )
        != "false",
        typing_indicator=os.getenv(
            "ENABLE_TYPING_INDICATOR", "true"
        )
        != "false",
    )

    if not ai.openai_api_key and not ai.anthropic_api_key and not ai.openrouter_api_key:
        raise RuntimeError(
            "At least one AI provider must be configured "
            "(OPENAI_API_KEY or ANTHROPIC_API_KEY or OPENROUTER_API_KEY)"
        )

    settings = Settings(
        slack=slack,
        ai=ai,
        rag=rag,
        memory=memory,
        app=app,
        security=security,
        features=features,
        rag_enabled=rag.enabled,
        memory_enabled=memory.enabled,
        slack_bot_token=slack.bot_token,
        slack_app_token=slack.app_token,
        slack_signing_secret=slack.signing_secret,
        dm_policy=security.dm_policy,
    )

    return settings


# Global settings instances
settings = load_settings()
config = settings
