import os
from typing import Optional


class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    whisper_model: str = os.getenv("WHISPER_MODEL", "large-v3")
    use_whisperx: bool = os.getenv("USE_WHISPERX", "false").lower() == "true"
    tts_provider: str = os.getenv("TTS_PROVIDER", "elevenlabs").lower()
    elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_voice_id: Optional[str] = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    base_data_dir: str = os.getenv("DATA_DIR", "/app/data")
    results_base_url: str = os.getenv("RESULTS_BASE_URL", "/results")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")


settings = Settings()
