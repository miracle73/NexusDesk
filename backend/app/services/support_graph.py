from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.services.knowledge import knowledge, openrouter_client


class SupportState(TypedDict, total=False):
    tenant_id: str
    question: str
    context: list[dict]
    decision: str
    answer: str
    escalation_reason: str | None


def retrieve(state: SupportState) -> SupportState:
    return {**state, "context": knowledge.search(state["tenant_id"], state["question"])}


def decide(state: SupportState) -> SupportState:
    question = state["question"].strip()
    urgent = ("human", "agent", "refund", "legal", "complaint", "cancel")
    if any(word in question.lower() for word in urgent):
        return {**state, "decision": "escalate", "escalation_reason": "Customer request requires human review"}
    if len(question.split()) < 3 or not state["context"]:
        return {**state, "decision": "clarify"}
    return {**state, "decision": "answer"}


def respond(state: SupportState) -> SupportState:
    if state["decision"] == "escalate":
        return {**state, "answer": "I’m handing this to a human support specialist who can help further."}
    if state["decision"] == "clarify":
        return {**state, "answer": "Could you share a little more detail so I can find the right answer?"}
    context = "\n\n".join(f"[{item['filename']}] {item['text']}" for item in state["context"])
    client = openrouter_client()
    if client is None:
        return {**state, "answer": state["context"][0]["text"]}
    result = client.chat.completions.create(model=settings.openrouter_model, temperature=0.2, messages=[
        {"role": "system", "content": "You are NexusDesk support. Answer only from the supplied company knowledge. Be concise and do not invent facts."},
        {"role": "user", "content": f"Company knowledge:\n{context}\n\nCustomer question: {state['question']}"},
    ])
    return {**state, "answer": result.choices[0].message.content or "I couldn't produce an answer."}


builder = StateGraph(SupportState)
builder.add_node("retrieve", retrieve)
builder.add_node("decide", decide)
builder.add_node("respond", respond)
builder.set_entry_point("retrieve")
builder.add_edge("retrieve", "decide")
builder.add_edge("decide", "respond")
builder.add_edge("respond", END)
support_graph = builder.compile()
