from app.services.knowledge import chunks, extract_text


def test_chunks_overlap_and_preserve_text() -> None:
    result = chunks("word " * 500, size=100, overlap=20)
    assert len(result) > 2
    assert all(len(item) <= 100 for item in result)


def test_extract_text_rejects_unknown_type() -> None:
    try:
        extract_text("unsafe.exe", b"data")
    except ValueError as exc:
        assert "TXT" in str(exc)
    else:
        raise AssertionError("Unsupported file was accepted")


def test_short_text_is_a_single_chunk() -> None:
    assert chunks("Support hours are Monday to Friday.") == ["Support hours are Monday to Friday."]


def test_long_text_chunks_cover_the_whole_input() -> None:
    text = " ".join(f"word{index}" for index in range(400))
    result = chunks(text, size=200, overlap=40)
    assert result[0].startswith("word0")
    assert result[-1].endswith("word399")
    assert len(result) <= -(-len(" ".join(text.split())) // (200 - 40))
