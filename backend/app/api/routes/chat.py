from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import Principal, current_user
from app.services.support_graph import support_graph
from app.store import repository

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    customer_email: str | None = None


def conversation_id_of(item: dict) -> str:
    return item["sk"].split("#", 1)[1]


@router.post("")
def chat(data: ChatRequest, user: Principal = Depends(current_user)) -> dict:
    if data.conversation_id:
        conversation = repository.get_conversation(user.tenant_id, data.conversation_id)
        if not conversation:
            raise HTTPException(404, "Conversation not found")
    else:
        conversation = repository.create_conversation(user.tenant_id, data.customer_email)
    conversation_id = conversation_id_of(conversation)

    repository.add_message(conversation_id, "user", data.message)
    result = support_graph.invoke({"tenant_id": user.tenant_id, "question": data.message})
    sources = sorted({item["filename"] for item in result.get("context", [])})

    status = conversation.get("status", repository.OPEN)
    changes: dict = {"status": status}
    if result["decision"] == "escalate":
        status = repository.ESCALATED
        changes = {"status": status, "escalation_reason": result.get("escalation_reason", "")}
    repository.set_conversation(user.tenant_id, conversation_id, changes)
    repository.add_message(conversation_id, "assistant", result["answer"], result["decision"], sources)
    return {
        "conversation_id": conversation_id,
        "answer": result["answer"],
        "decision": result["decision"],
        "sources": sources,
        "status": status,
    }
