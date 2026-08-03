import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models import Conversation, ConversationStatus, Message, User
from app.services.support_graph import support_graph

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    customer_email: str | None = None


@router.post("")
def chat(data: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    conversation = db.get(Conversation, data.conversation_id) if data.conversation_id else None
    if conversation and conversation.tenant_id != user.tenant_id:
        raise HTTPException(404, "Conversation not found")
    if not conversation:
        conversation = Conversation(tenant_id=user.tenant_id, customer_email=data.customer_email)
        db.add(conversation)
        db.flush()
    db.add(Message(conversation_id=conversation.id, role="user", content=data.message))
    result = support_graph.invoke({"tenant_id": user.tenant_id, "question": data.message})
    sources = sorted({item["filename"] for item in result.get("context", [])})
    if result["decision"] == "escalate":
        conversation.status = ConversationStatus.escalated
        conversation.escalation_reason = result.get("escalation_reason")
    db.add(Message(conversation_id=conversation.id, role="assistant", content=result["answer"], decision=result["decision"], sources=json.dumps(sources)))
    db.commit()
    return {"conversation_id": conversation.id, "answer": result["answer"], "decision": result["decision"], "sources": sources, "status": conversation.status}
