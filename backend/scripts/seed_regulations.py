"""Seed RAG documents from backend/data/regulations.

Run inside backend container:
    python -m scripts.seed_regulations
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from app.ai.chatbot.vectorstore import ingest_document
from app.db.session import AsyncSessionLocal


REGULATIONS_DIR = Path(__file__).resolve().parents[1] / "data" / "regulations"
SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


async def main() -> None:
    REGULATIONS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in REGULATIONS_DIR.iterdir() if path.suffix.lower() in SUPPORTED)
    if not files:
        print(f"Không có tài liệu trong {REGULATIONS_DIR}")
        return

    total_chunks = 0
    async with AsyncSessionLocal() as db:
        for path in files:
            documents = await ingest_document(
                db,
                filename=path.name,
                data=path.read_bytes(),
                uploaded_by=None,
                replace_existing=True,
            )
            total_chunks += len(documents)
            print(f"OK {path.name}: {len(documents)} chunks")

    print(f"Done. Seeded {len(files)} files, {total_chunks} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
