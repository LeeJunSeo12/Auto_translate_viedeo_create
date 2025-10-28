import os

from app.providers.factory import get_tts_provider


def test_provider_fallback_gtts(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "gtts")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    provider = get_tts_provider()
    assert provider.__class__.__name__ == "GTTSProvider"
