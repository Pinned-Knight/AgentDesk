"""Deterministic offline provider: rule-based intent routing + template responses.

Lets the whole stack (agent graph, tools, streaming, persistence) run and be tested with no API
key. The same `rule_classify` doubles as the live provider's fallback when the remote LLM fails.
"""

import asyncio
import re
from datetime import datetime
from typing import AsyncIterator

from app.llm.base import Classification, ResponseContext
from app.tools import ORDER_ID_RE

HUMAN_RE = re.compile(
    r"\b(human|real person|live agent|agent|representative|supervisor|manager|speak to|talk to|"
    r"complain\w*|angry|furious|terrible|worst|scam|fraud|unacceptable|lawsuit)\b", re.I)
RETURN_RE = re.compile(r"\b(return\w*|refund\w*|exchange\w*|send (?:it )?back|money back|replace\w*)\b", re.I)
POLICY_RE = re.compile(r"\b(policy|policies|how long|how many days|how do|how does|what is|what's|what are|do you|can i)\b", re.I)
STATUS_RE = re.compile(r"\b(where|track\w*|status|arriv\w*|eta|when (?:will|does|is)|delay\w*|late|received|shipped|dispatched)\b", re.I)
MY_ORDER_RE = re.compile(r"\bmy (?:order|package|parcel|item|delivery|shipment|purchase)\b", re.I)
HOWTO_RE = re.compile(r"^\s*(how|what)\b", re.I)
FAQ_RE = re.compile(
    r"\b(ship\w*|deliver\w*|pay\w*|cancel\w*|warrant\w*|address\w*|international\w*|abroad|overseas|gift\w*|"
    r"hours|support|timing|damag\w*|broken|defective|faulty|upi|cards?|polic\w+|track\w*)\b", re.I)
SMALLTALK_RE = re.compile(r"^\s*(hi|hello|hey|yo|good (?:morning|afternoon|evening)|thanks?|thank you|bye|goodbye|ok(?:ay)?|cool|great)\b", re.I)


def rule_classify(message: str) -> Classification:
    oid = ORDER_ID_RE.search(message)
    entities = {"order_id": oid.group(0).upper()} if oid else {}

    if HUMAN_RE.search(message):
        return Classification("human_handoff", 0.95, entities)
    if RETURN_RE.search(message):
        if not oid and POLICY_RE.search(message):
            return Classification("faq", 0.85, entities)
        return Classification("return_refund", 0.9 if oid else 0.72, entities)
    if not oid and HOWTO_RE.search(message) and (FAQ_RE.search(message) or STATUS_RE.search(message)):
        return Classification("faq", 0.8, entities)
    if oid or (MY_ORDER_RE.search(message) and STATUS_RE.search(message)):
        return Classification("order_status", 0.92 if oid else 0.78, entities)
    if SMALLTALK_RE.search(message) and len(message.split()) <= 6:
        return Classification("smalltalk", 0.9, entities)
    if FAQ_RE.search(message):
        return Classification("faq", 0.8, entities)
    return Classification("unknown", 0.3, entities)


def _day(value: str | None) -> str:
    if not value:
        return "soon"
    return datetime.fromisoformat(value.rstrip("Z")).strftime("%b %d").replace(" 0", " ")


def _call(ctx: ResponseContext, name: str) -> dict | None:
    return next((c["result"] for c in ctx.tool_results if c["name"] == name), None)


class MockLLM:
    name = "mock"

    def __init__(self, token_delay_s: float = 0.012):
        self.token_delay_s = token_delay_s

    async def classify(self, message: str, history: list[dict[str, str]]) -> Classification:
        return rule_classify(message)

    async def respond(self, ctx: ResponseContext) -> AsyncIterator[str]:
        text = self._compose(ctx)
        for chunk in re.findall(r"\S+\s*", text):
            yield chunk
            if self.token_delay_s:
                await asyncio.sleep(self.token_delay_s)

    # -- templates ---------------------------------------------------------------
    def _compose(self, ctx: ResponseContext) -> str:
        if ctx.escalated:
            return (f"I've escalated this to a human specialist and opened ticket {ctx.ticket_id}. "
                    "You'll hear back within 2 hours (support hours: 9am-9pm IST, Mon-Sat). "
                    "Is there anything you'd like me to add to the ticket?")
        return getattr(self, f"_{ctx.intent}", self._unknown)(ctx)

    def _order_status(self, ctx: ResponseContext) -> str:
        r = _call(ctx, "get_order_status")
        if r is None:
            return "Happy to check - could you share your order ID? It looks like ORD-1234."
        if not r.get("found"):
            return f"I couldn't find an order with ID {r['order_id']}. Could you double-check it?"
        oid, item, status = r["order_id"], r["item"], r["status"]
        if status == "delivered":
            return f"Good news - {oid} ({item}) was delivered on {_day(r['delivered_at'])}. Want help with a return or anything else?"
        if status == "shipped":
            return (f"{oid} ({item}) has shipped with {r['carrier']} (tracking {r['tracking']}) "
                    f"and is expected on {_day(r['eta'])}.")
        if status == "out_for_delivery":
            return f"{oid} ({item}) is out for delivery today with {r['carrier']} (tracking {r['tracking']}). It should reach you soon!"
        if status == "processing":
            return f"{oid} ({item}) is being prepared and should ship within 24 hours. I can cancel it if you'd like."
        return f"{oid} ({item}) was cancelled, and any payment is refunded to your original payment method."

    def _return_refund(self, ctx: ResponseContext) -> str:
        r = _call(ctx, "initiate_return")
        if r is None:
            return "I can start a return for you - which order is it? (for example ORD-1234)"
        oid, reason = r.get("order_id"), r.get("reason")
        if r.get("created"):
            return (f"Done! I've started a return for {oid} ({r['item']}). Your return ID is {r['rma_id']}. "
                    f"Drop the package at any partner point within 7 days and your refund of ${r['price']:.2f} "
                    "will reach your original payment method 5-7 business days after pickup.")
        if reason == "already_requested":
            return f"A return for {oid} is already in progress (return ID {r['rma_id']}), so you're all set."
        if reason == "order_not_found":
            return f"I couldn't find an order with ID {oid}. Could you double-check it?"
        if reason == "window_expired":
            return (f"{oid} was delivered {r['days_since_delivery']} days ago, which is outside our 30-day return "
                    "window, so I can't start an automatic return. Want me to connect you with a human agent to review it?")
        if reason == "not_delivered_yet":
            return (f"{oid} hasn't been delivered yet (status: {r['status'].replace('_', ' ')}), so it can't be returned "
                    "yet. If you no longer want it, I can help cancel it or you can refuse delivery.")
        return f"{oid} was already cancelled, so there's nothing to return - your refund is on its way to the original payment method."

    def _faq(self, ctx: ResponseContext) -> str:
        if not ctx.kb:
            return self._unknown(ctx)
        return f"{ctx.kb[0]['answer']} Is there anything else I can help with?"

    def _smalltalk(self, ctx: ResponseContext) -> str:
        m = ctx.message.lower()
        if "thank" in m:
            return "You're welcome! Anything else I can help with?"
        if "bye" in m:
            return "Goodbye! Reach out any time - I'm here 24/7."
        return "Hi! I'm AgentDesk's support assistant. I can track orders, start returns and answer policy questions. How can I help?"

    def _unknown(self, ctx: ResponseContext) -> str:
        return ("I'm not sure I understood that. I can help with order tracking, returns and refunds, and store policies - "
                "or I can connect you with a human agent. What would you like to do?")
