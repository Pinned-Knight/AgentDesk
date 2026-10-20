from fastapi import APIRouter, Request

from app.schemas import AnalyticsResponse, DailyCount, IntentCount, ToolCount

router = APIRouter(tags=["analytics"])

_ASSISTANT = {"$match": {"role": "assistant"}}


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(request: Request):
    """Aggregations run inside MongoDB ($group / $unwind / $dateToString), not in Python."""
    db = request.app.state.deps.db

    async def agg(*stages: dict) -> list[dict]:
        return await db.messages.aggregate([_ASSISTANT, *stages]).to_list(length=None)

    totals = await agg({"$group": {
        "_id": None, "turns": {"$sum": 1}, "avg_latency": {"$avg": "$latency_ms"},
        "escalated": {"$sum": {"$cond": ["$escalated", 1, 0]}}, "cached": {"$sum": {"$cond": ["$cached", 1, 0]}}}})
    intents = await agg({"$group": {"_id": "$intent", "count": {"$sum": 1}}}, {"$sort": {"count": -1, "_id": 1}})
    tool_usage = await agg({"$unwind": "$tools"}, {"$group": {"_id": "$tools.name", "count": {"$sum": 1}}},
                           {"$sort": {"count": -1, "_id": 1}})
    daily = await agg({"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                                  "count": {"$sum": 1}}}, {"$sort": {"_id": 1}})

    t = totals[0] if totals else {"turns": 0, "avg_latency": 0, "escalated": 0, "cached": 0}
    turns = t["turns"] or 0
    return AnalyticsResponse(
        total_conversations=await db.conversations.count_documents({}),
        total_messages=await db.messages.count_documents({}),
        escalation_rate=round(t["escalated"] / turns, 3) if turns else 0.0,
        avg_latency_ms=round(t["avg_latency"] or 0, 1),
        cache_hit_rate=round(t["cached"] / turns, 3) if turns else 0.0,
        intents=[IntentCount(intent=i["_id"] or "unknown", count=i["count"]) for i in intents],
        tools=[ToolCount(name=i["_id"], count=i["count"]) for i in tool_usage],
        daily=[DailyCount(date=d["_id"], count=d["count"]) for d in daily])
