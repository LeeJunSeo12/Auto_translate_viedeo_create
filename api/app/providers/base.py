from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, texts: Iterable[str], out_path: Path) -> None:
        ...
