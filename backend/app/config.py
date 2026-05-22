from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # AI Provider
    openai_api_key: Optional[str] = None
    openai_compatible_api_key: Optional[str] = None
    openai_compatible_base_url: str = "https://api.openai.com/v1"
    openai_compatible_model: str = "gpt-4o-mini"

    # Local Whisper (fallback for audio transcription)
    local_whisper_model: str = "/app/models/faster-whisper-small"
    local_whisper_device: str = "auto"
    local_whisper_compute_type: str = "auto"

    # Subtitles
    bilibili_session_token: Optional[str] = None
    savesubs_x_auth_token: Optional[str] = None

    # Cache
    redis_url: Optional[str] = None
    upstash_redis_rest_url: Optional[str] = None
    upstash_redis_rest_token: Optional[str] = None

    # Server
    backend_port: int = 8000

    # CORS
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
