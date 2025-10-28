import os
import re
from typing import List
import requests

try:
    from deep_translator import GoogleTranslator  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    GoogleTranslator = None  # type: ignore


def contains_hangul(text: str) -> bool:
    return bool(re.search(r"[\uAC00-\uD7A3]", text))


def translate_to_korean_natural(text: str) -> str:
    """Translate any input to Korean using GoogleTranslator when available.

    Falls back to original text if translator is unavailable or errors occur.
    """
    if not text.strip():
        return text
    # 1) Prefer OpenAI if configured
    provider = os.getenv("TRANSLATION_PROVIDER", "").lower()
    api_key = os.getenv("OPENAI_API_KEY")
    if provider == "openai" and api_key:
        try:
            model = os.getenv("OPENAI_TRANSLATE_MODEL", "gpt-4o-mini")
            # Chunk by ~6000 chars for OpenAI; conservative for safety
            chunks: List[str] = []
            buf = []
            size = 0
            for part in re.split(r"(\n{2,})", text):
                part_len = len(part)
                if size + part_len > 6000 and buf:
                    chunks.append("".join(buf))
                    buf, size = [part], part_len
                else:
                    buf.append(part)
                    size += part_len
            if buf:
                chunks.append("".join(buf))

            out: List[str] = []
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            system_prompt = (
                "You are a professional Korean translator and editor. Translate the user's text into natural, fluent Korean, "
                "preserving meaning, tone, and context. Use consistent terminology, readable sentence flow, and appropriate honorifics. "
                "Do not add explanations. Output only the translated Korean text."
            )
            for ch in chunks:
                payload = {
                    "model": model,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": ch},
                    ],
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                out.append(data["choices"][0]["message"]["content"].strip())
            return "\n\n".join(out)
        except Exception:
            # Soft-fallback to Google
            pass

    # 2) Fallback to GoogleTranslator (no key required)
    if GoogleTranslator is None:
        return text
    try:
        # Chunk by ~4000 chars to satisfy API limits
        chunks: List[str] = []
        buf = []
        size = 0
        for part in re.split(r"(\n{2,})", text):
            part_len = len(part)
            if size + part_len > 4000 and buf:
                chunks.append("".join(buf))
                buf, size = [part], part_len
            else:
                buf.append(part)
                size += part_len
        if buf:
            chunks.append("".join(buf))

        translated: List[str] = []
        translator = GoogleTranslator(source="auto", target="ko")
        for ch in chunks:
            translated.append(translator.translate(ch))
        return "".join(translated)
    except Exception:
        return text


def split_text_for_tts(text: str, max_chars: int = 250) -> List[str]:
    """Sentence-aware chunking with soft limit by characters.

    Keeps sentences together when possible for more natural prosody in TTS.
    """
    # Split by sentence terminators (handles .,!,?, … and CJK punctuation)
    sentences = re.split(r"(?<=[\.!?。！？…])\s+", text.strip())
    chunks: List[str] = []
    buf: List[str] = []
    cur = 0
    for sent in sentences:
        s = sent.strip()
        if not s:
            continue
        # Ensure sentence ends with punctuation for natural cadence
        if not re.search(r"[\.!?。！？…]$", s):
            s = s + "."
        if cur + len(s) + (1 if buf else 0) <= max_chars:
            buf.append(s)
            cur += len(s) + (1 if buf else 0)
        else:
            if buf:
                chunks.append(" ".join(buf))
            buf = [s]
            cur = len(s)
    if buf:
        chunks.append(" ".join(buf))
    return chunks
