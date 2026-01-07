"""Configuration management for Codex CLI."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for Codex CLI."""
    
    # OpenRouter settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "anthropic/claude-haiku-4.5")
    
    # Application settings
    APP_NAME = "Codex CLI"
    MAX_TOKENS = 20000
    TEMPERATURE = 0
    
    # Model routing - sort by throughput (speed)
    ROUTE_BY = "throughput"
    
    # Workspace settings
    WORKSPACE_PATH = Path.cwd()
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        return True
