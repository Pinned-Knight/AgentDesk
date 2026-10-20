import json

import httpx
import pytest

from app.llm.base import ResponseContext
from app.llm.mock import MockLLM, rule_classify
from app.llm.openai_compat import OpenAICompatLLM


@pytest.mark.parametrize("text,intent", [
    ("Where is my order ORD-1002?", "order_status"),
    ("Track ORD-1005", "order_status"),
    ("I want to return ORD-1001", "return_refund"),
    ("I need a refund for ORD-1007", "return_refund"),
    ("What is your refund policy?", "faq"),
    ("How long does shipping take?", "faq"),
    ("Do you ship internationally?", "faq"),
    ("How do I track my order?", "faq"),
    ("I'd like to speak to a human", "human_handoff"),
    ("this is unacceptable", "human_handoff"),
    ("hello", "smalltalk"),
    ("thanks!", "smalltalk"),
    ("asdf qwerty", "unknown"),
])
def test_rule_based_intents(text, intent):
    assert rule_classify(text).intent == intent


def _ctx(**kw) -> ResponseContext:
    base = dict(message="where is it", history=[], intent="order_status", entities={}, tool_results=[], kb=[])
    return ResponseContext(**{**base, **kw})


async def _collect(stream) -> str:
    return "".join([chunk async for chunk in stream])


async def test_mock_reply_is_grounded_in_tool_results():
    result = {"found": True, "order_id": "ORD-1", "item": "Lamp", "status": "shipped", "carrier": "BlueDart",
              "tracking": "T123", "eta": "2026-10-23T00:00:00Z", "delivered_at": None}
    text = await _collect(MockLLM(0).respond(_ctx(tool_results=[{"name": "get_order_status", "args": {}, "result": result}])))
    assert "ORD-1" in text and "T123" in text and "Oct 23" in text


# --- OpenAI-compatible provider, exercised against a mocked HTTP transport -------------------------
def _llm(handler) -> OpenAICompatLLM:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAICompatLLM("https://llm.test/v1", "sk-test", "test-model", client=client)


def _completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


async def test_classify_parses_json_mode_reply():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(auth=request.headers["authorization"], url=str(request.url), body=json.loads(request.content))
        return _completion(json.dumps({"intent": "order_status", "confidence": 0.88, "entities": {"order_id": "ord-1002"}}))

    cls = await _llm(handler).classify("where is it", [])
    assert (cls.intent, cls.confidence, cls.entities) == ("order_status", 0.88, {"order_id": "ORD-1002"})
    assert seen["auth"] == "Bearer sk-test" and seen["url"] == "https://llm.test/v1/chat/completions"
    assert seen["body"]["model"] == "test-model" and seen["body"]["response_format"] == {"type": "json_object"}


async def test_classify_tolerates_fenced_json_and_unknown_intents():
    fenced = '```json\n{"intent": "banana", "confidence": 7, "entities": {"order_id": "nope"}}\n```'
    cls = await _llm(lambda r: _completion(fenced)).classify("x", [])
    assert (cls.intent, cls.confidence, cls.entities) == ("unknown", 1.0, {})


async def test_classify_retries_without_json_mode_when_unsupported():
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if "response_format" in bodies[-1]:
            return httpx.Response(400, json={"error": "response_format not supported"})
        return _completion('{"intent": "faq", "confidence": 0.7, "entities": {}}')

    cls = await _llm(handler).classify("what is your policy", [])
    assert cls.intent == "faq" and len(bodies) == 2 and "response_format" not in bodies[1]


async def test_classify_falls_back_to_rules_when_the_endpoint_fails():
    cls = await _llm(lambda r: httpx.Response(500)).classify("Where is my order ORD-1002?", [])
    assert cls.intent == "order_status" and cls.entities == {"order_id": "ORD-1002"}


def _sse(*tokens: str) -> bytes:
    events = "".join(f"data: {json.dumps({'choices': [{'delta': {'content': t}}]})}\n\n" for t in tokens)
    return (events + "data: [DONE]\n\n").encode()


async def test_respond_streams_tokens_with_grounding():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=_sse("Hel", "lo ", "there"), headers={"content-type": "text/event-stream"})

    ctx = _ctx(tool_results=[{"name": "get_order_status", "args": {}, "result": {"found": True, "order_id": "ORD-1002"}}])
    assert await _collect(_llm(handler).respond(ctx)) == "Hello there"
    assert seen["body"]["stream"] is True and "ORD-1002" in seen["body"]["messages"][-1]["content"]


async def test_respond_falls_back_to_template_when_the_endpoint_is_down():
    text = await _collect(_llm(lambda r: httpx.Response(503)).respond(_ctx(intent="smalltalk", message="hello")))
    assert "AgentDesk" in text
