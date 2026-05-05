import sys
import os

sys.path.append("/app")

from app.ai.chatbot.rag import parse_document_bytes, chunk_pages

with open(__file__, "rb") as f:
    data = f.read()

try:
    pages = parse_document_bytes("test.txt", data)
    chunks = chunk_pages(pages)
    print("Chunks count:", len(chunks))
    if chunks:
        print("First chunk:", chunks[0].content[:100])
except Exception as e:
    print("Error:", e)
