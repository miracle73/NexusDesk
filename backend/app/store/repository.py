"""Tenant-scoped data access over the single DynamoDB table.

Key layout (pk / sk):
  TENANT#<tenant_id>          META
  USER#<email>                META                      -> holds tenant_id
  TENANT#<tenant_id>          DOC#<created_at>#<doc_id>
  TENANT#<tenant_id>          CONV#<conversation_id>
  CONV#<conversation_id>      MSG#<created_at>#<msg_id>
  TENANT#<tenant_id>#VEC      <doc_id>#<chunk>
"""
from datetime import UTC, datetime
from uuid import uuid4

from app.store import dynamo

OPEN = "open"
RESOLVED = "resolved"
ESCALATED = "escalated"
STATUSES = (OPEN, RESOLVED, ESCALATED)


def new_id() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(UTC).isoformat()


def create_tenant(name: str, slug: str) -> dict:
    tenant = {"pk": f"TENANT#{new_id()}", "sk": "META", "name": name, "slug": slug, "created_at": now()}
    dynamo.put(tenant)
    return {"id": tenant["pk"].split("#", 1)[1], "name": name, "slug": slug}


def get_user(email: str) -> dict | None:
    return dynamo.get(f"USER#{email.lower()}", "META")


def create_user(email: str, password_hash: str, tenant_id: str) -> dict:
    user = {
        "pk": f"USER#{email.lower()}",
        "sk": "META",
        "id": new_id(),
        "email": email.lower(),
        "password_hash": password_hash,
        "tenant_id": tenant_id,
        "created_at": now(),
    }
    dynamo.put(user)
    return user


def get_tenant(tenant_id: str) -> dict | None:
    return dynamo.get(f"TENANT#{tenant_id}", "META")


def add_document(tenant_id: str, filename: str, content_type: str, chunk_count: int, s3_key: str | None) -> dict:
    created_at = now()
    document_id = new_id()
    dynamo.put({
        "pk": f"TENANT#{tenant_id}",
        "sk": f"DOC#{created_at}#{document_id}",
        "id": document_id,
        "filename": filename,
        "content_type": content_type,
        "chunk_count": chunk_count,
        "s3_key": s3_key,
        "created_at": created_at,
    })
    return {"id": document_id, "filename": filename, "chunk_count": chunk_count, "created_at": created_at}


def list_documents(tenant_id: str) -> list[dict]:
    items = dynamo.query(f"TENANT#{tenant_id}", "DOC#")
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return [
        {"id": item["id"], "filename": item["filename"], "chunk_count": int(item.get("chunk_count", 0)), "created_at": item["created_at"]}
        for item in items
    ]


def create_conversation(tenant_id: str, customer_email: str | None) -> dict:
    timestamp = now()
    conversation = {
        "pk": f"TENANT#{tenant_id}",
        "sk": f"CONV#{new_id()}",
        "customer_email": customer_email,
        "status": OPEN,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    dynamo.put(conversation)
    return conversation


def get_conversation(tenant_id: str, conversation_id: str) -> dict | None:
    return dynamo.get(f"TENANT#{tenant_id}", f"CONV#{conversation_id}")


def set_conversation(tenant_id: str, conversation_id: str, values: dict) -> None:
    dynamo.update(f"TENANT#{tenant_id}", f"CONV#{conversation_id}", {**values, "updated_at": now()})


def list_conversations(tenant_id: str, status: str | None = None) -> list[dict]:
    items = dynamo.query(f"TENANT#{tenant_id}", "CONV#")
    if status:
        items = [item for item in items if item.get("status") == status]
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return items


def add_message(conversation_id: str, role: str, content: str, decision: str | None = None, sources: list[str] | None = None) -> dict:
    created_at = now()
    message = {
        "pk": f"CONV#{conversation_id}",
        "sk": f"MSG#{created_at}#{new_id()[:8]}",
        "role": role,
        "content": content,
        "decision": decision,
        "sources": sources or None,
        "created_at": created_at,
    }
    dynamo.put(message)
    return message


def list_messages(conversation_id: str) -> list[dict]:
    return dynamo.query(f"CONV#{conversation_id}", "MSG#")
