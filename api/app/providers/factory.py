from app.config import settings
from app.providers.base import TTSProvider
from app.providers.gtts_provider import GTTSProvider

try:
    from app.providers.elevenlabs_provider import ElevenLabsProvider
except Exception:  # pragma: no cover - missing key etc
    ElevenLabsProvider = None  # type: ignore

try:
    from app.providers.azure_provider import AzureTTSStub
except Exception:
    AzureTTSStub = None  # type: ignore


def get_tts_provider() -> TTSProvider:
    name = (settings.tts_provider or "gtts").lower()
    if name == "elevenlabs" and ElevenLabsProvider is not None and settings.elevenlabs_api_key:
        return ElevenLabsProvider()
    if name == "azure" and AzureTTSStub is not None:
        return AzureTTSStub()
    return GTTSProvider()
