from app.utils.text import split_text_for_tts


def test_split_text_for_tts_basic():
    text = "안녕하세요 이것은 한국어 문장 분할 테스트 입니다. 길이를 제한합니다."
    chunks = split_text_for_tts(text, max_chars=20)
    assert all(len(c) <= 20 for c in chunks)
    assert "".join(chunks).replace(" ", "").startswith("안녕하세요")
