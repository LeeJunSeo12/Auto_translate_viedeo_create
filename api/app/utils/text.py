from typing import List


def split_text_for_tts(text: str, max_chars: int = 250) -> List[str]:
    chunks: List[str] = []
    buf: str = ""
    for token in text.split():
        if len(buf) + len(token) + 1 <= max_chars:
            buf = f"{buf} {token}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = token
    if buf:
        chunks.append(buf)
    return chunks
