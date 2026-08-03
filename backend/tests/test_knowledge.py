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
