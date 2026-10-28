from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import Principal, current_user
from app.store import repository

router = APIRouter()


def serialize(item: dict, messages: list[dict] | None = None) -> dict:
    value = {
        "id": item["sk"].split("#", 1)[1],
        "customer_email": item.get("customer_email"),
        "status": item.get("status", repository.OPEN),
        "escalation_reason": item.get("escalation_reason"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }
    if messages is not None:
        value["messages"] = [
            {
                "id": message["sk"],
                "role": message["role"],
                "content": message["content"],
                "decision": message.get("decision"),
                "created_at": message["created_at"],
            }
            for message in messages
        ]
    return value


@router.get("")
def list_conversations(status: str | None = Query(None), user: Principal = Depends(current_user)) -> list[dict]:
    if status and status not in repository.STATUSES:
        raise HTTPException(422, "Unknown status")
    return [serialize(item) for item in repository.list_conversations(user.tenant_id, status)]


@router.get("/metrics")
def metrics(user: Principal = Depends(current_user)) -> dict:
    items = repository.list_conversations(user.tenant_id)
    counts = dict.fromkeys(repository.STATUSES, 0)
    for item in items:
        status = item.get("status", repository.OPEN)
        counts[status] = counts.get(status, 0) + 1
    total = len(items)
    gaps: list[str] = []
    for item in items:
        if item.get("status") != repository.ESCALATED or len(gaps) >= 10:
            continue
        conversation_id = item["sk"].split("#", 1)[1]
        questions = [msg["content"] for msg in repository.list_messages(conversation_id) if msg["role"] == "user"]
        gaps.extend(questions[-1:])
    return {
        "total": total,
        "open": counts["open"],
        "resolved": counts["resolved"],
        "escalated": counts["escalated"],
        "resolution_rate": round(counts["resolved"] / total * 100, 1) if total else 0,
        "knowledge_gaps": gaps[:10],
    }


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, user: Principal = Depends(current_user)) -> dict:
    item = repository.get_conversation(user.tenant_id, conversation_id)
    if not item:
        raise HTTPException(404, "Conversation not found")
    return serialize(item, repository.list_messages(conversation_id))


@router.patch("/{conversation_id}/status")
def update_status(conversation_id: str, status: str, user: Principal = Depends(current_user)) -> dict:
    if status not in repository.STATUSES:
        raise HTTPException(422, "Unknown status")
    item = repository.get_conversation(user.tenant_id, conversation_id)
    if not item:
        raise HTTPException(404, "Conversation not found")
    repository.set_conversation(user.tenant_id, conversation_id, {"status": status})
    return serialize({**item, "status": status})
