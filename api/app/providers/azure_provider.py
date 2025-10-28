from pathlib import Path
from typing import Iterable

from app.providers.base import TTSProvider


class AzureTTSStub(TTSProvider):
    def synthesize(self, texts: Iterable[str], out_path: Path) -> None:
        # Stub: not implemented yet; just writes empty mp3
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(b"")
