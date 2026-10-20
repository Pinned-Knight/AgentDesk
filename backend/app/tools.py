"""Business tools the agent can call. All return JSON-serialisable dicts."""

import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.utils import iso, utcnow

ORDER_ID_RE = re.compile(r"\bORD-\d{4}\b", re.I)
RETURN_WINDOW_DAYS = 30

_STOPWORDS = {
    "the", "and", "for", "you", "your", "are", "does", "did", "can", "how", "what", "with", "this", "that",
    "from", "have", "has", "will", "would", "could", "there", "about", "please", "our", "was", "were", "any",
}


def _serialise(doc: dict) -> dict:
    return {k: (iso(v) if isinstance(v, datetime) else v) for k, v in doc.items()}


# --- orders -------------------------------------------------------------------
async def get_order_status(db: Any, order_id: str) -> dict:
    order = await db.orders.find_one({"order_id": order_id.upper()}, {"_id": 0})
    if order is None:
        return {"found": False, "order_id": order_id.upper()}
    return {"found": True, **_serialise(order)}


async def check_return_eligibility(db: Any, order_id: str) -> dict:
    order = await db.orders.find_one({"order_id": order_id.upper()}, {"_id": 0})
    if order is None:
        return {"eligible": False, "reason": "order_not_found", "order_id": order_id.upper()}
    base = {k: order[k] for k in ("order_id", "item", "price", "status")}
    if order["status"] == "cancelled":
        return {**base, "eligible": False, "reason": "order_cancelled"}
    if order["status"] != "delivered":
        return {**base, "eligible": False, "reason": "not_delivered_yet"}
    days = (utcnow() - order["delivered_at"]).days
    if days > RETURN_WINDOW_DAYS:
        return {**base, "eligible": False, "reason": "window_expired", "days_since_delivery": days}
    return {**base, "eligible": True, "days_left": RETURN_WINDOW_DAYS - days}


async def initiate_return(db: Any, session_id: str, order_id: str, reason: str) -> dict:
    """Create a return request if the order is eligible (idempotent per order)."""
    result = await check_return_eligibility(db, order_id)
    if not result["eligible"]:
        return {**result, "created": False}
    existing = await db.returns.find_one({"order_id": result["order_id"]}, {"_id": 0})
    if existing:
        return {**result, "created": False, "reason": "already_requested", "rma_id": existing["rma_id"]}
    rma_id = f"RMA-{uuid4().hex[:6].upper()}"
    await db.returns.insert_one({
        "rma_id": rma_id, "order_id": result["order_id"], "session_id": session_id,
        "reason": reason[:200], "status": "requested", "created_at": utcnow(),
    })
    return {**result, "created": True, "rma_id": rma_id}


# --- tickets ------------------------------------------------------------------
async def create_ticket(db: Any, session_id: str, summary: str, priority: str = "normal") -> dict:
    ticket = {
        "ticket_id": f"TCK-{uuid4().hex[:6].upper()}", "session_id": session_id,
        "summary": summary[:200], "priority": priority, "status": "open", "created_at": utcnow(),
    }
    await db.tickets.insert_one(dict(ticket))
    return _serialise(ticket)


# --- FAQ retrieval ---------------------------------------------------------------
def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            if suffix == "s" and word.endswith("ss"):
                continue
            word = word[: -len(suffix)]
            break
    if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz":  # shipp -> ship
        word = word[:-1]
    return word


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if len(w) > 2 and w not in _STOPWORDS}


async def search_faq(db: Any, query: str, k: int = 2, min_score: float = 0.25) -> list[dict]:
    """Lightweight lexical retrieval: stemmed token overlap, question + keywords weighted over answer."""
    q = _tokens(query)
    if not q:
        return []
    scored = []
    async for faq in db.faqs.find({}, {"_id": 0}):
        title = _tokens(faq["question"]) | _tokens(" ".join(faq.get("keywords", [])))
        body = _tokens(faq["answer"])
        score = (2 * len(q & title) + len(q & body)) / (2 * len(q))
        if score >= min_score:
            scored.append({"id": faq["id"], "question": faq["question"], "answer": faq["answer"],
                           "score": round(min(score, 1.0), 3)})
    scored.sort(key=lambda m: m["score"], reverse=True)
    return scored[:k]
