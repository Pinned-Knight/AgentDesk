from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import ConversationDetail, ConversationSummary, StoredMessage, ToolCall
from app.utils import iso

router = APIRouter(tags=["conversations"])


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(request: Request, limit: int = Query(20, ge=1, le=100)):
    db = request.app.state.deps.db
    docs = await db.conversations.find({}, {"_id": 0}).sort("last_message_at", -1).limit(limit).to_list(length=limit)
    return [ConversationSummary(
        session_id=d["session_id"], started_at=iso(d["started_at"]), last_message_at=iso(d["last_message_at"]),
        turns=d.get("turns", 0), last_intent=d.get("last_intent"), escalated=d.get("escalated", False))
        for d in docs]


@router.get("/conversations/{session_id}", response_model=ConversationDetail)
async def get_conversation(session_id: str, request: Request):
    db = request.app.state.deps.db
    docs = await db.messages.find({"session_id": session_id}, {"_id": 0}).sort("created_at", 1).to_list(length=500)
    if not docs:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(session_id=session_id, messages=[
        StoredMessage(role=d["role"], content=d["content"], intent=d.get("intent"),
                      tools=[ToolCall(**t) for t in d.get("tools", [])], escalated=d.get("escalated", False),
                      latency_ms=d.get("latency_ms"), created_at=iso(d["created_at"]))
        for d in docs])
