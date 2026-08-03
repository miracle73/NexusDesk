import hashlib
import io
import math
from pathlib import Path

import chromadb
from openai import OpenAI
from pypdf import PdfReader

from app.core.config import settings


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return data.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    raise ValueError("Only TXT, Markdown and PDF files are supported")


def chunks(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    clean = " ".join(text.split())
    if not clean:
        return []
    result, start = [], 0
    while start < len(clean):
        end = min(len(clean), start + size)
        if end < len(clean):
            split = clean.rfind(" ", start, end)
            end = split if split > start + size // 2 else end
        result.append(clean[start:end])
        start = max(end - overlap, start + 1)
    return result


class KnowledgeStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    def _collection(self, tenant_id: str):
        return self.client.get_or_create_collection(f"tenant_{tenant_id.replace('-', '_')}", metadata={"hnsw:space": "cosine"})

    def _embeddings(self, texts: list[str]) -> list[list[float]]:
        if settings.openrouter_api_key:
            client = OpenAI(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)
            try:
                return [item.embedding for item in client.embeddings.create(model=settings.embedding_model, input=texts).data]
            except Exception:
                pass
        # Deterministic local fallback keeps development, tests, and ingestion available offline.
        vectors = []
        for text in texts:
            vector = [0.0] * 256
            for word in text.lower().split():
                digest = hashlib.sha256(word.encode()).digest()
                vector[int.from_bytes(digest[:2], "big") % len(vector)] += 1
            norm = math.sqrt(sum(value * value for value in vector)) or 1
            vectors.append([value / norm for value in vector])
        return vectors

    def add(self, tenant_id: str, document_id: str, filename: str, texts: list[str]) -> None:
        self._collection(tenant_id).upsert(
            ids=[f"{document_id}:{i}" for i in range(len(texts))],
            documents=texts,
            embeddings=self._embeddings(texts),
            metadatas=[{"document_id": document_id, "filename": filename, "chunk": i} for i in range(len(texts))],
        )

    def search(self, tenant_id: str, query: str, limit: int = 4) -> list[dict]:
        collection = self._collection(tenant_id)
        if collection.count() == 0:
            return []
        result = collection.query(query_embeddings=self._embeddings([query]), n_results=min(limit, collection.count()))
        return [{"text": text, "filename": meta["filename"], "distance": distance} for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])]


knowledge = KnowledgeStore()
