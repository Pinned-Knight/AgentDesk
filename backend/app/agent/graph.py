"""LangGraph workflow: guardrail -> understand -> (tools | retrieve | escalate) -> respond.

Nodes stream progress through an `emit(event, data)` callback passed via the run config, so the
same compiled graph serves both the JSON endpoint (no-op emitter) and the SSE endpoint.
"""

import re
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app import tools
from app.guardrails import REFUSAL, check_input
from app.llm.base import LLMProvider, ResponseContext


class AgentState(TypedDict, total=False):
    session_id: str
    message: str
    history: list[dict]
    guardrail_flags: list[str]
    intent: str
    confidence: float
    entities: dict
    next_step: str
    tools: list[dict]
    kb: list[dict]
    reply: str
    escalated: bool
    ticket_id: str | None


NEXT_STEP = {
    "order_status": "run_tools",
    "return_refund": "run_tools",
    "faq": "retrieve",
    "human_handoff": "escalate",
}


def last_order_id(history: list[dict]) -> str | None:
    """Conversation memory: most recent order ID the customer mentioned."""
    for turn in reversed(history):
        if turn.get("role") == "user":
            match = tools.ORDER_ID_RE.search(turn.get("content", ""))
            if match:
                return match.group(0).upper()
    return None


def _chunks(text: str) -> list[str]:
    return re.findall(r"\S+\s*", text)


def build_graph(db: Any, llm: LLMProvider):
    async def emit(config: RunnableConfig, event: str, data: dict) -> None:
        fn = (config or {}).get("configurable", {}).get("emit")
        if fn is not None:
            await fn(event, data)

    async def guardrail(state: AgentState, config: RunnableConfig) -> dict:
        result = check_input(state["message"])
        await emit(config, "trace", {"step": "guardrail", "flags": result.flags})
        update: dict = {"message": result.clean_message, "guardrail_flags": result.flags,
                        "tools": [], "kb": [], "escalated": False, "ticket_id": None}
        if "prompt_injection" in result.flags:
            update.update(intent="unknown", confidence=1.0, entities={})
        return update

    async def understand(state: AgentState, config: RunnableConfig) -> dict:
        cls = await llm.classify(state["message"], state.get("history", []))
        entities: dict = dict(cls.entities)
        if cls.intent in ("order_status", "return_refund") and not entities.get("order_id"):
            remembered = last_order_id(state.get("history", []))
            if remembered:
                entities.update(order_id=remembered, order_id_source="memory")
        next_step = NEXT_STEP.get(cls.intent, "respond")
        await emit(config, "trace", {"step": "understand", "intent": cls.intent,
                                     "confidence": cls.confidence, "entities": entities})
        await emit(config, "trace", {"step": "route", "next": next_step})
        return {"intent": cls.intent, "confidence": cls.confidence, "entities": entities, "next_step": next_step}

    async def run_tools(state: AgentState, config: RunnableConfig) -> dict:
        order_id = state["entities"].get("order_id")
        calls: list[dict] = []
        if order_id and state["intent"] == "order_status":
            calls.append({"name": "get_order_status", "args": {"order_id": order_id},
                          "result": await tools.get_order_status(db, order_id)})
        elif order_id and state["intent"] == "return_refund":
            reason = state["message"]
            calls.append({"name": "initiate_return", "args": {"order_id": order_id, "reason": reason[:80]},
                          "result": await tools.initiate_return(db, state["session_id"], order_id, reason)})
        for call in calls:
            await emit(config, "tool", call)
        await emit(config, "trace", {"step": "tools", "names": [c["name"] for c in calls]})
        return {"tools": calls}

    async def retrieve(state: AgentState, config: RunnableConfig) -> dict:
        matches = await tools.search_faq(db, state["message"])
        call = {"name": "search_faq", "args": {"query": state["message"][:120]},
                "result": {"matches": [{"id": m["id"], "question": m["question"], "score": m["score"]} for m in matches]}}
        await emit(config, "trace", {"step": "retrieve", "matches": call["result"]["matches"]})
        await emit(config, "tool", call)
        return {"kb": matches, "tools": [call]}

    async def escalate(state: AgentState, config: RunnableConfig) -> dict:
        args = {"summary": state["message"][:120], "priority": "high"}
        ticket = await tools.create_ticket(db, state["session_id"], state["message"], priority="high")
        await emit(config, "trace", {"step": "escalate", "ticket_id": ticket["ticket_id"]})
        await emit(config, "tool", {"name": "create_ticket", "args": args, "result": ticket})
        return {"escalated": True, "ticket_id": ticket["ticket_id"],
                "tools": [{"name": "create_ticket", "args": args, "result": ticket}]}

    async def respond(state: AgentState, config: RunnableConfig) -> dict:
        parts: list[str] = []
        if "prompt_injection" in state.get("guardrail_flags", []):
            await emit(config, "trace", {"step": "respond", "provider": "guardrail"})
            chunks = _chunks(REFUSAL)
        else:
            await emit(config, "trace", {"step": "respond", "provider": llm.name})
            ctx = ResponseContext(
                message=state["message"], history=state.get("history", []), intent=state["intent"],
                entities=state.get("entities", {}), tool_results=state.get("tools", []), kb=state.get("kb", []),
                escalated=state.get("escalated", False), ticket_id=state.get("ticket_id"))
            chunks = llm.respond(ctx)
        if isinstance(chunks, list):
            for chunk in chunks:
                parts.append(chunk)
                await emit(config, "token", {"text": chunk})
        else:
            async for chunk in chunks:
                parts.append(chunk)
                await emit(config, "token", {"text": chunk})
        return {"reply": "".join(parts).strip()}

    graph = StateGraph(AgentState)
    graph.add_node("guardrail", guardrail)
    graph.add_node("understand", understand)
    graph.add_node("run_tools", run_tools)
    graph.add_node("retrieve", retrieve)
    graph.add_node("escalate", escalate)
    graph.add_node("respond", respond)

    graph.add_edge(START, "guardrail")
    graph.add_conditional_edges(
        "guardrail",
        lambda s: "respond" if "prompt_injection" in s.get("guardrail_flags", []) else "understand",
        {"respond": "respond", "understand": "understand"})
    graph.add_conditional_edges(
        "understand", lambda s: s["next_step"],
        {"run_tools": "run_tools", "retrieve": "retrieve", "escalate": "escalate", "respond": "respond"})
    for node in ("run_tools", "retrieve", "escalate"):
        graph.add_edge(node, "respond")
    graph.add_edge("respond", END)
    return graph.compile()
