from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import Principal, current_user
from app.core.config import settings
from app.services.knowledge import chunks, extract_text, knowledge, upload_to_s3
from app.store import repository

router = APIRouter()


@router.post("", status_code=201)
def upload(file: UploadFile = File(...), user: Principal = Depends(current_user)) -> dict:
    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        limit = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(413, f"Maximum file size is {limit} MB")
    try:
        text_chunks = chunks(extract_text(file.filename or "", data))
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from None
    if not text_chunks:
        raise HTTPException(422, "No readable text found")
    filename = file.filename or "document"
    content_type = file.content_type or "application/octet-stream"
    s3_key = upload_to_s3(user.tenant_id, filename, data, content_type)
    document = repository.add_document(user.tenant_id, filename, content_type, len(text_chunks), s3_key)
    knowledge.add(user.tenant_id, document["id"], filename, text_chunks)
    return {"id": document["id"], "filename": filename, "chunk_count": document["chunk_count"]}


@router.get("")
def list_documents(user: Principal = Depends(current_user)) -> list[dict]:
    return repository.list_documents(user.tenant_id)
