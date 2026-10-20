"""Demo catalogue: a handful of orders in every lifecycle state plus a small FAQ knowledge base."""

from datetime import datetime, timedelta

from app.utils import utcnow


def build_orders(now: datetime | None = None) -> list[dict]:
    now = now or utcnow()
    ago = lambda days: now - timedelta(days=days)  # noqa: E731
    ahead = lambda days: now + timedelta(days=days)  # noqa: E731
    return [
        {"order_id": "ORD-1001", "item": "Wireless Earbuds", "price": 59.99, "status": "delivered",
         "carrier": "BlueDart", "tracking": "BD4417201", "placed_at": ago(8), "delivered_at": ago(3), "eta": None},
        {"order_id": "ORD-1002", "item": "Trail Running Shoes", "price": 89.00, "status": "shipped",
         "carrier": "Delhivery", "tracking": "DL9921034", "placed_at": ago(4), "delivered_at": None, "eta": ahead(2)},
        {"order_id": "ORD-1003", "item": "Pour-Over Coffee Maker", "price": 42.50, "status": "processing",
         "carrier": None, "tracking": None, "placed_at": ago(1), "delivered_at": None, "eta": ahead(5)},
        {"order_id": "ORD-1004", "item": "Canvas Backpack", "price": 64.00, "status": "delivered",
         "carrier": "BlueDart", "tracking": "BD3302981", "placed_at": ago(50), "delivered_at": ago(45), "eta": None},
        {"order_id": "ORD-1005", "item": "Phone Case", "price": 12.99, "status": "out_for_delivery",
         "carrier": "Ecom Express", "tracking": "EE7781120", "placed_at": ago(3), "delivered_at": None, "eta": now},
        {"order_id": "ORD-1006", "item": "Bluetooth Speaker", "price": 35.00, "status": "cancelled",
         "carrier": None, "tracking": None, "placed_at": ago(6), "delivered_at": None, "eta": None},
        {"order_id": "ORD-1007", "item": "LED Desk Lamp", "price": 27.45, "status": "delivered",
         "carrier": "Delhivery", "tracking": "DL5540019", "placed_at": ago(14), "delivered_at": ago(10), "eta": None},
        {"order_id": "ORD-1008", "item": "Yoga Mat", "price": 24.00, "status": "shipped",
         "carrier": "BlueDart", "tracking": "BD8810477", "placed_at": ago(2), "delivered_at": None, "eta": ahead(4)},
    ]


FAQS: list[dict] = [
    {"id": "faq-shipping", "question": "How long does shipping take?",
     "answer": "Standard shipping takes 3-5 business days and express takes 1-2 business days. Orders over $50 ship free.",
     "keywords": ["delivery", "deliver", "courier", "dispatch", "speed", "days", "ship"]},
    {"id": "faq-returns", "question": "What is your return and refund policy?",
     "answer": "You can return most items within 30 days of delivery in their original condition. Refunds go back to your original payment method within 5-7 business days of us receiving the item.",
     "keywords": ["refund", "return", "money back", "exchange", "policy", "refunds"]},
    {"id": "faq-cancel", "question": "Can I cancel my order?",
     "answer": "Orders can be cancelled free of charge until they ship. Once shipped, you can refuse delivery or start a return after it arrives.",
     "keywords": ["cancel", "cancellation", "stop order"]},
    {"id": "faq-payment", "question": "Which payment methods do you accept?",
     "answer": "We accept all major credit and debit cards, UPI, net banking and popular wallets.",
     "keywords": ["pay", "payment", "card", "upi", "wallet", "netbanking", "credit", "debit", "methods"]},
    {"id": "faq-tracking", "question": "How do I track my order?",
     "answer": "Share your order ID (like ORD-1002) and I'll fetch live tracking, or use the tracking link in your shipping confirmation email.",
     "keywords": ["track", "tracking", "where", "status", "locate"]},
    {"id": "faq-address", "question": "Can I change my delivery address?",
     "answer": "Addresses can be updated until the order ships. After that, please contact the carrier with your tracking number.",
     "keywords": ["address", "change", "update", "relocate", "location"]},
    {"id": "faq-warranty", "question": "Do products come with a warranty?",
     "answer": "Electronics carry a 12-month manufacturer warranty. Keep your invoice and I'll help you raise a claim.",
     "keywords": ["warranty", "guarantee", "repair", "defect"]},
    {"id": "faq-international", "question": "Do you ship internationally?",
     "answer": "Yes, to 40+ countries. International delivery takes 7-14 business days, and duties and taxes are shown at checkout.",
     "keywords": ["international", "abroad", "overseas", "countries", "global", "worldwide"]},
    {"id": "faq-giftcards", "question": "How do gift cards work?",
     "answer": "Gift cards are emailed instantly, never expire, and can be applied at checkout.",
     "keywords": ["gift", "voucher", "coupon", "giftcard"]},
    {"id": "faq-hours", "question": "What are your support hours?",
     "answer": "The AI assistant is available 24/7, and human agents are available 9am-9pm IST, Monday to Saturday.",
     "keywords": ["hours", "support", "timing", "open", "available", "contact"]},
    {"id": "faq-damaged", "question": "My item arrived damaged - what do I do?",
     "answer": "Sorry about that! Share your order ID and I'll start a replacement or refund right away. Photos help but aren't required.",
     "keywords": ["damaged", "broken", "defective", "faulty", "wrong item", "missing"]},
]
