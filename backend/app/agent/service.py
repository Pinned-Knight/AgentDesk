"""One customer turn end-to-end: memory + cache -> agent graph -> persistence."""

import re
import time
from datetime import timedelta
from typing import Awaitable, Callable

from app.deps import Deps
from app.schemas import ChatRequest, ChatResponse, ToolCall
from app.utils import utcnow

Emitter = Callable[[str, dict], Awaitable[None]]


async def _noop(event: str, data: dict) -> None:
    return None


async def run_turn(deps: Deps, req: ChatRequest, emit: Emitter | None = None) -> ChatResponse:
    emit = emit or _noop
    started = time.perf_counter()
    history = await deps.cache.history(req.session_id)

    cached = await deps.cache.get_cached(req.message)
    await emit("trace", {"step": "cache", "hit": cached is not None})

    if cached:  # replay a previously computed FAQ answer without touching the LLM
        state = {**cached, "message": req.message, "guardrail_flags": [], "escalated": False, "ticket_id": None}
        await emit("trace", {"step": "understand", "intent": cached["intent"],
                             "confidence": cached["confidence"], "entities": {}})
        for call in cached["tools"]:
            await emit("tool", call)
        await emit("trace", {"step": "respond", "provider": "cache"})
        for chunk in re.findall(r"\S+\s*", cached["reply"]):
            await emit("token", {"text": chunk})
    else:
        state = await deps.graph.ainvoke(
            {"session_id": req.session_id, "message": req.message, "history": history},
            config={"configurable": {"emit": emit}})

    flags = state.get("guardrail_flags", [])
    guardrail = "prompt_injection" if "prompt_injection" in flags else ("pii_masked" if flags else None)
    response = ChatResponse(
        session_id=req.session_id, reply=state["reply"], intent=state["intent"],
        confidence=round(float(state["confidence"]), 3),
        tools=[ToolCall(**t) for t in state.get("tools", [])],
        escalated=state.get("escalated", False), ticket_id=state.get("ticket_id"),
        latency_ms=round((time.perf_counter() - started) * 1000, 1),
        cached=cached is not None, guardrail=guardrail)

    clean_message = state["message"]
    if not cached and response.intent == "faq" and not flags and state.get("kb"):
        await deps.cache.set_cached(req.message, {
            "reply": response.reply, "intent": response.intent, "confidence": response.confidence,
            "tools": [t.model_dump() for t in response.tools]})

    await _persist(deps, req.session_id, clean_message, response)
    await deps.cache.remember(req.session_id, "user", clean_message)
    await deps.cache.remember(req.session_id, "assistant", response.reply)
    return response


async def _persist(deps: Deps, session_id: str, user_text: str, resp: ChatResponse) -> None:
    now = utcnow()
    await deps.db.messages.insert_many([
        {"session_id": session_id, "role": "user", "content": user_text, "intent": None, "tools": [],
         "escalated": False, "latency_ms": None, "cached": False, "created_at": now},
        {"session_id": session_id, "role": "assistant", "content": resp.reply, "intent": resp.intent,
         "confidence": resp.confidence, "tools": [t.model_dump() for t in resp.tools],
         "escalated": resp.escalated, "latency_ms": resp.latency_ms, "cached": resp.cached,
         "guardrail": resp.guardrail, "created_at": now + timedelta(milliseconds=1)},
    ])
    update: dict = {"$setOnInsert": {"started_at": now}, "$inc": {"turns": 1},
                    "$set": {"last_message_at": now, "last_intent": resp.intent}}
    if resp.escalated:
        update["$set"]["escalated"] = True
    else:
        update["$setOnInsert"]["escalated"] = False
    await deps.db.conversations.update_one({"session_id": session_id}, update, upsert=True)
