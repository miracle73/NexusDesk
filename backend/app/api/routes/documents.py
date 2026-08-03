from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models import Document, User
from app.services.knowledge import chunks, extract_text, knowledge

router = APIRouter()


@router.post("", status_code=201)
def upload(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    data = file.file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 10 MB")
    try:
        text_chunks = chunks(extract_text(file.filename or "", data))
    except ValueError as exc:
        raise HTTPException(415, str(exc))
    if not text_chunks:
        raise HTTPException(422, "No readable text found")
    document = Document(tenant_id=user.tenant_id, filename=file.filename or "document", content_type=file.content_type or "application/octet-stream", chunk_count=len(text_chunks))
    db.add(document)
    db.commit()
    db.refresh(document)
    knowledge.add(user.tenant_id, document.id, document.filename, text_chunks)
    return {"id": document.id, "filename": document.filename, "chunk_count": document.chunk_count}


@router.get("")
def list_documents(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    docs = db.scalars(select(Document).where(Document.tenant_id == user.tenant_id).order_by(Document.created_at.desc())).all()
    return [{"id": doc.id, "filename": doc.filename, "chunk_count": doc.chunk_count, "created_at": doc.created_at} for doc in docs]
