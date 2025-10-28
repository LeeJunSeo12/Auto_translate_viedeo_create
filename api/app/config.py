import os
from typing import Optional

try:
    # Load environment variables from .env if present (for local runs)
    from dotenv import load_dotenv, find_dotenv  # type: ignore

    load_dotenv(find_dotenv())
except Exception:
    pass


def _default_redis_url() -> str:
    """Use container hostname inside Docker, localhost when running locally."""
    in_docker = os.path.exists("/.dockerenv") or os.getenv("IN_DOCKER") == "1"
    return "redis://redis:6379/0" if in_docker else "redis://localhost:6379/0"


class Settings:
    redis_url: str = os.getenv("REDIS_URL", _default_redis_url())
    whisper_model: str = os.getenv("WHISPER_MODEL", "large-v3")
    use_whisperx: bool = os.getenv("USE_WHISPERX", "false").lower() == "true"
    tts_provider: str = os.getenv("TTS_PROVIDER", "elevenlabs").lower()
    elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_voice_id: Optional[str] = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    base_data_dir: str = os.getenv("DATA_DIR", "/app/data")
    results_base_url: str = os.getenv("RESULTS_BASE_URL", "/results")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    use_sadtalker: bool = os.getenv("USE_SADTALKER", "false").lower() == "true"
    sadtalker_repo: str = os.getenv("SADTALKER_REPO", "/app/extern/SadTalker")
    sadtalker_checkpoint_dir: str = os.getenv("SADTALKER_CKPT_DIR", "/app/extern/SadTalker/checkpoints")


settings = Settings()
