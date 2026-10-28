"""Document parsing, S3 storage, and tenant-isolated embeddings kept in DynamoDB."""
import base64
import hashlib
import io
import math
import struct
from pathlib import Path

from openai import OpenAI
from pypdf import PdfReader

from app.core.config import settings
from app.store import dynamo

VECTOR_SIZE = 256


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


def _pack(vector: list[float]) -> str:
    return base64.b64encode(struct.pack(f"<{len(vector)}f", *vector)).decode()


def _unpack(value: str) -> list[float]:
    raw = base64.b64decode(value)
    return list(struct.unpack(f"<{len(raw) // 4}f", raw))


def _local_vector(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    for word in text.lower().split():
        digest = hashlib.sha256(word.encode()).digest()
        vector[int.from_bytes(digest[:2], "big") % VECTOR_SIZE] += 1
    norm = math.sqrt(sum(value * value for value in vector)) or 1
    return [value / norm for value in vector]


def embeddings(texts: list[str]) -> list[list[float]]:
    """Hashing embeddings: no paid embedding endpoint, deterministic and free."""
    return [_local_vector(text) for text in texts]


def upload_to_s3(tenant_id: str, filename: str, data: bytes, content_type: str) -> str | None:
    if not settings.uploads_bucket:
        return None
    key = f"tenants/{tenant_id}/{filename}"
    dynamo.s3().put_object(Bucket=settings.uploads_bucket, Key=key, Body=data, ContentType=content_type)
    return key


class KnowledgeStore:
    """Embeddings live under a tenant-prefixed partition key, so no query can cross tenants."""

    @staticmethod
    def _pk(tenant_id: str) -> str:
        return f"TENANT#{tenant_id}#VEC"

    def add(self, tenant_id: str, document_id: str, filename: str, texts: list[str]) -> None:
        texts = texts[: settings.max_vector_chunks]
        for index, (text, vector) in enumerate(zip(texts, embeddings(texts), strict=True)):
            dynamo.put({
                "pk": self._pk(tenant_id),
                "sk": f"{document_id}#{index:04d}",
                "document_id": document_id,
                "filename": filename,
                "text": text,
                "vector": _pack(vector),
            })

    def search(self, tenant_id: str, query: str, limit: int = 4) -> list[dict]:
        items = dynamo.query(self._pk(tenant_id), limit=settings.max_vector_chunks)
        if not items:
            return []
        target = embeddings([query])[0]
        scored = []
        for item in items:
            vector = _unpack(item["vector"])
            score = sum(a * b for a, b in zip(target, vector, strict=False))
            scored.append({"text": item["text"], "filename": item["filename"], "distance": 1 - score, "score": score})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return [{k: v for k, v in item.items() if k != "score"} for item in scored[:limit] if item["score"] > 0]


knowledge = KnowledgeStore()


def openrouter_client() -> OpenAI | None:
    if not settings.openrouter_api_key:
        return None
    return OpenAI(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)
