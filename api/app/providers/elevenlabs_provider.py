import io
import os
from pathlib import Path
from typing import Iterable

import requests

from app.config import settings
from app.utils.logging import get_logger
from app.providers.base import TTSProvider


logger = get_logger(__name__)


class ElevenLabsProvider(TTSProvider):
    def __init__(self) -> None:
        api_key = settings.elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is required for ElevenLabs provider")
        self.api_key = api_key
        self.voice_id = settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"

    def synthesize(self, texts: Iterable[str], out_path: Path) -> None:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {"xi-api-key": self.api_key, "accept": "audio/mpeg", "Content-Type": "application/json"}

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as fout:
            for text in texts:
                payload = {
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                fout.write(resp.content)
