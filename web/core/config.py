"""
Configuration management for Paper Companion Web Backend.
Loads settings from environment variables and .env file.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    Required settings:
    - ANTHROPIC_API_KEY: API key for Claude
    - DATABASE_PATH: Path to SQLite database file

    Optional settings:
    - ZOTERO_API_KEY: API key for Zotero integration
    - ZOTERO_LIBRARY_ID: Zotero library ID (user or group)
    - ZOTERO_LIBRARY_TYPE: Type of library ('user' or 'group'), defaults to 'user'
    """

    # Required settings
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude",
        validation_alias="ANTHROPIC_API_KEY"
    )

    database_path: str = Field(
        default="data/paper_companion.db",
        description="Path to SQLite database file",
        validation_alias="DATABASE_PATH"
    )

    # Optional Zotero settings
    zotero_api_key: Optional[str] = Field(
        default=None,
        description="Zotero API key (optional)",
        validation_alias="ZOTERO_API_KEY"
    )

    zotero_library_id: Optional[str] = Field(
        default=None,
        description="Zotero library ID (optional)",
        validation_alias="ZOTERO_LIBRARY_ID"
    )

    zotero_library_type: str = Field(
        default="user",
        description="Zotero library type: 'user' or 'group'",
        validation_alias="ZOTERO_LIBRARY_TYPE"
    )

    # Application settings
    app_name: str = Field(
        default="Paper Companion API",
        description="Application name"
    )

    debug: bool = Field(
        default=False,
        description="Enable debug mode",
        validation_alias="DEBUG"
    )

    # Model configuration for pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_anthropic_key(cls, v: str) -> str:
        """Validate that Anthropic API key is provided and non-empty."""
        if not v or not v.strip():
            raise ValueError("ANTHROPIC_API_KEY is required and cannot be empty")
        return v.strip()

    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, v: str) -> str:
        """Ensure database directory exists."""
        db_path = Path(v)
        # Create parent directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)

    @field_validator("zotero_library_type")
    @classmethod
    def validate_library_type(cls, v: str) -> str:
        """Validate Zotero library type."""
        if v not in ("user", "group"):
            raise ValueError("ZOTERO_LIBRARY_TYPE must be 'user' or 'group'")
        return v

    def has_zotero_config(self) -> bool:
        """Check if Zotero is properly configured."""
        return bool(self.zotero_api_key and self.zotero_library_id)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton pattern).

    Returns:
        Settings: Application settings
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function for dependency injection in FastAPI
def get_settings_dependency() -> Settings:
    """FastAPI dependency for injecting settings."""
    return get_settings()
