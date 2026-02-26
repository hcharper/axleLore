"""Configuration management for RigSherpa.

Targets: Raspberry Pi 5 (8GB) with Qwen3 1.7B via Ollama.
All inference runs locally, fully offline.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root relative to this file: src/backend/core/config.py -> project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Application settings."""

    # Application info
    app_name: str = "RigSherpa"
    app_version: str = "0.2.0"
    debug: bool = False

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Database (async sqlite)
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'db' / 'rigsherpa.db'}"

    # Paths
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = _PROJECT_ROOT / "data"
    chromadb_dir: Path = _PROJECT_ROOT / "data" / "chromadb"
    vehicles_config_dir: Path = _PROJECT_ROOT / "config" / "vehicles"
    logs_dir: Path = _PROJECT_ROOT / "data" / "logs"

    # LLM settings — optimised for Pi 5 8GB
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:1.7b"
    ollama_fallback_model: str = "gemma3:1b"
    ollama_timeout: int = 120
    llm_temperature: float = 0.4
    llm_max_tokens: int = 1024

    # Embedding model (loaded in-process, ~25 MB)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    # RAG settings
    chunk_size: int = 600
    chunk_overlap: int = 100
    retrieval_top_k: int = 5
    similarity_threshold: float = 0.65

    # OBD2 settings
    obd2_enabled: bool = False
    obd2_port: Optional[str] = None
    obd2_baudrate: int = 38400
    obd2_protocol: Optional[str] = None
    obd2_timeout: int = 10

    # Vehicle settings
    default_vehicle: str = "fzj80"

    # Update server (used by check-update.sh and system API)
    update_base_url: str = "https://api.rigsherpa.com"

    # Logging
    log_level: str = "INFO"
    log_file: str = str(_PROJECT_ROOT / "data" / "logs" / "rigsherpa.log")

    # CORS (for development)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (FastAPI dependency-injection compatible)."""
    return settings
