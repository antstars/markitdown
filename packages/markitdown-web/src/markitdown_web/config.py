import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    password: str
    secret_key: str
    max_file_mb: int
    max_batch: int
    ttl_minutes: int
    max_workers: int
    temp_root: Path
    enable_plugins: bool
    openai_api_key: str | None
    llm_model: str
    docintel_endpoint: str | None
    url_timeout_seconds: int

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024


def load_settings() -> Settings:
    return Settings(
        password=os.getenv("MARKITDOWN_WEB_PASSWORD", "markitdown"),
        secret_key=os.getenv("MARKITDOWN_WEB_SECRET_KEY", secrets.token_urlsafe(32)),
        max_file_mb=_env_int("MARKITDOWN_WEB_MAX_FILE_MB", 50),
        max_batch=_env_int("MARKITDOWN_WEB_MAX_BATCH", 20),
        ttl_minutes=_env_int("MARKITDOWN_WEB_TTL_MINUTES", 60),
        max_workers=_env_int("MARKITDOWN_WEB_MAX_WORKERS", 2),
        temp_root=Path(os.getenv("MARKITDOWN_WEB_TEMP_DIR", "")) if os.getenv("MARKITDOWN_WEB_TEMP_DIR") else Path.cwd() / ".markitdown-web",
        enable_plugins=_env_bool("MARKITDOWN_ENABLE_PLUGINS", False),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        llm_model=os.getenv("MARKITDOWN_LLM_MODEL", "gpt-4o"),
        docintel_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        url_timeout_seconds=_env_int("MARKITDOWN_WEB_URL_TIMEOUT_SECONDS", 20),
    )
