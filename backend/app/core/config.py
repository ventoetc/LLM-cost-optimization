"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # API Keys
    OPENROUTER_API_KEY: str = ""
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./llm_optimizer.db"

    # Redis
    REDIS_URL: Optional[str] = None

    # Application
    APP_NAME: str = "LLM Cost Optimizer"
    DEBUG: bool = True
    LOG_LEVEL: str = "info"

    # Model Configuration
    DECOMPOSER_MODEL: str = "anthropic/claude-3-haiku"
    BASELINE_MODEL: str = "anthropic/claude-opus-4-5"
    DEFAULT_ROUTER_STRATEGY: str = "learning"

    # Cost tracking (cents per million tokens)
    MODEL_COSTS: dict = {
        "anthropic/claude-3-haiku": {"input": 25, "output": 125},
        "anthropic/claude-3-5-sonnet": {"input": 300, "output": 1500},
        "anthropic/claude-opus-4-5": {"input": 1500, "output": 7500},
        "openai/gpt-3.5-turbo": {"input": 50, "output": 150},
        "openai/gpt-4-turbo": {"input": 1000, "output": 3000},
        "openai/gpt-4o": {"input": 250, "output": 1000},
    }

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
