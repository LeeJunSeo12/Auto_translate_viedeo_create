from pathlib import Path
from typing import Iterable

from gtts import gTTS

from app.providers.base import TTSProvider


class GTTSProvider(TTSProvider):
    def synthesize(self, texts: Iterable[str], out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # gTTS는 멀티 청크를 직접 이어붙이기 까다로우므로 단일 텍스트로 합친다.
        full_text = "\n".join(texts)
        tts = gTTS(text=full_text, lang="ko")
        tts.save(str(out_path))
