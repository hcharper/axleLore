"""Configuration management for AxleLore."""
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application info
    app_name: str = "AxleLore"
    app_version: str = "0.1.0"
    debug: bool = False

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Database
    database_url: str = "sqlite:///./data/db/axlelore.db"

    # Paths
    data_dir: Path = Path("./data")
    vehicles_dir: Path = Path("./data/vehicles")
    logs_dir: Path = Path("./data/logs")

    # LLM settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct-q4_K_M"
    ollama_timeout: int = 120
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # RAG settings
    chunk_size: int = 800
    chunk_overlap: int = 100
    retrieval_top_k: int = 5
    similarity_threshold: float = 0.7

    # OBD2 settings
    obd2_enabled: bool = False
    obd2_port: Optional[str] = None
    obd2_baudrate: int = 38400
    obd2_protocol: Optional[str] = None
    obd2_timeout: int = 10

    # Vehicle settings
    default_vehicle: str = "fzj80"

    # Logging
    log_level: str = "INFO"
    log_file: str = "./data/logs/axlelore.log"

    # CORS (for development)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings
