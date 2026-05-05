import pytest

from app.ai.chatbot.providers import HashEmbeddingProvider
from app.ai.chatbot.rag import chunk_pages, parse_document_bytes


def test_parse_text_document_and_chunk():
    pages = parse_document_bytes(
        "quy-che.txt",
        "Điều 1. Sinh viên cần theo dõi GPA.\nĐiều 2. Cảnh báo học vụ.".encode("utf-8"),
    )
    chunks = chunk_pages(pages)

    assert len(chunks) == 1
    assert "Cảnh báo học vụ" in chunks[0].content


@pytest.mark.asyncio
async def test_hash_embedding_is_768_dimensional_and_stable():
    provider = HashEmbeddingProvider()
    first = await provider.embed("cảnh báo học vụ")
    second = await provider.embed("cảnh báo học vụ")

    assert len(first) == 768
    assert first == second
    assert any(value != 0 for value in first)
