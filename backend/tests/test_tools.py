import pytest
from mongomock_motor import AsyncMongoMockClient

from app import tools
from app.db import ensure_indexes, seed


@pytest.fixture
async def db():
    database = AsyncMongoMockClient()["unit"]
    await ensure_indexes(database)
    await seed(database)
    return database


async def test_seed_is_idempotent(db):
    await seed(db)
    assert await db.orders.count_documents({}) == 8 and await db.faqs.count_documents({}) == 11


async def test_order_lookup_is_case_insensitive(db):
    result = await tools.get_order_status(db, "ord-1003")
    assert result["found"] and result["order_id"] == "ORD-1003" and result["status"] == "processing"


@pytest.mark.parametrize("order_id,eligible,reason", [
    ("ORD-1001", True, None),
    ("ORD-1007", True, None),
    ("ORD-1004", False, "window_expired"),
    ("ORD-1002", False, "not_delivered_yet"),
    ("ORD-1006", False, "order_cancelled"),
    ("ORD-9999", False, "order_not_found"),
])
async def test_return_eligibility(db, order_id, eligible, reason):
    result = await tools.check_return_eligibility(db, order_id)
    assert result["eligible"] is eligible
    assert result.get("reason") == reason


async def test_initiate_return_is_idempotent_per_order(db):
    first = await tools.initiate_return(db, "sess-1", "ORD-1001", "changed my mind")
    again = await tools.initiate_return(db, "sess-2", "ORD-1001", "again")
    assert first["created"] and not again["created"] and again["reason"] == "already_requested"
    assert again["rma_id"] == first["rma_id"] and await db.returns.count_documents({}) == 1


async def test_create_ticket_persists(db):
    ticket = await tools.create_ticket(db, "sess-1", "refund is late", priority="high")
    assert ticket["ticket_id"].startswith("TCK-") and ticket["priority"] == "high"
    assert await db.tickets.count_documents({"ticket_id": ticket["ticket_id"]}) == 1


@pytest.mark.parametrize("query,expected", [
    ("how long does delivery take", "faq-shipping"),
    ("can I change my address", "faq-address"),
    ("which payment options do you have", "faq-payment"),
    ("do you offer a warranty", "faq-warranty"),
    ("is it possible to cancel", "faq-cancel"),
    ("do you ship internationally", "faq-international"),
    ("what is your refund policy", "faq-returns"),
])
async def test_faq_retrieval_top_hit(db, query, expected):
    matches = await tools.search_faq(db, query)
    assert matches and matches[0]["id"] == expected


async def test_faq_retrieval_returns_nothing_for_gibberish(db):
    assert await tools.search_faq(db, "qwerty asdf zxcv") == []
