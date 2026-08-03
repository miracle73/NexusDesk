from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user
from app.db.session import get_db
from app.models import Conversation, ConversationStatus, Message, User

router = APIRouter()


def serialize(item: Conversation, details: bool = False) -> dict:
    value = {"id": item.id, "customer_email": item.customer_email, "status": item.status, "escalation_reason": item.escalation_reason, "created_at": item.created_at, "updated_at": item.updated_at}
    if details:
        value["messages"] = [{"id": message.id, "role": message.role, "content": message.content, "decision": message.decision, "created_at": message.created_at} for message in item.messages]
    return value


@router.get("")
def list_conversations(status: ConversationStatus | None = Query(None), user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    query = select(Conversation).where(Conversation.tenant_id == user.tenant_id)
    if status:
        query = query.where(Conversation.status == status)
    return [serialize(item) for item in db.scalars(query.order_by(Conversation.updated_at.desc())).all()]


@router.get("/metrics")
def metrics(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(select(Conversation.status, func.count()).where(Conversation.tenant_id == user.tenant_id).group_by(Conversation.status)).all()
    counts = {status.value: count for status, count in rows}
    total = sum(counts.values())
    unresolved_questions = db.scalars(select(Message.content).join(Conversation).where(Conversation.tenant_id == user.tenant_id, Message.role == "user", Conversation.status == ConversationStatus.escalated).order_by(Message.created_at.desc()).limit(10)).all()
    return {"total": total, "open": counts.get("open", 0), "resolved": counts.get("resolved", 0), "escalated": counts.get("escalated", 0), "resolution_rate": round(counts.get("resolved", 0) / total * 100, 1) if total else 0, "knowledge_gaps": list(unresolved_questions)}


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    item = db.scalar(select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation_id, Conversation.tenant_id == user.tenant_id))
    if not item:
        raise HTTPException(404, "Conversation not found")
    return serialize(item, True)


@router.patch("/{conversation_id}/status")
def update_status(conversation_id: str, status: ConversationStatus, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    item = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.tenant_id == user.tenant_id))
    if not item:
        raise HTTPException(404, "Conversation not found")
    item.status = status
    db.commit()
    return serialize(item)
