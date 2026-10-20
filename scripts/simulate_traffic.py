"""Replay scripted customer conversations against a running AgentDesk API.

Useful for populating the analytics dashboard with real pipeline output:

    python scripts/simulate_traffic.py --base-url http://localhost:8000 --rounds 3
"""

import argparse
import random
import time
import uuid

import httpx

CONVERSATIONS = [
    ["Hi there", "Where is my order ORD-1002?", "Thanks!"],
    ["I want to return ORD-1001"],
    ["What is your refund policy?", "How long does shipping take?"],
    ["Track ORD-1005", "I want to return it"],
    ["I'd like to speak to a human"],
    ["Can I change my delivery address?"],
    ["I want to return ORD-1004", "I'd like to speak to a human"],
    ["Do you ship internationally?"],
    ["Where is my order ORD-1003?"],
    ["Which payment methods do you accept?"],
    ["My item arrived damaged"],
    ["What is your refund policy?"],
    ["Where is my order ORD-1008?"],
    ["this is unacceptable, my parcel is late"],
    ["asdf qwerty"],
]


def send(client: httpx.Client, base_url: str, session_id: str, message: str) -> None:
    while True:
        r = client.post(f"{base_url}/api/chat", json={"session_id": session_id, "message": message})
        if r.status_code == 429:
            time.sleep(r.json().get("retry_after", 5) + 1)
            continue
        r.raise_for_status()
        return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    random.seed(args.seed)
    sent = 0
    with httpx.Client(timeout=30) as client:
        for _ in range(args.rounds):
            for script in random.sample(CONVERSATIONS, k=len(CONVERSATIONS)):
                session_id = uuid.uuid4().hex
                for message in script:
                    send(client, args.base_url, session_id, message)
                    sent += 1
        stats = client.get(f"{args.base_url}/api/analytics").json()
    print(f"sent {sent} messages -> {stats['total_conversations']} conversations, "
          f"escalation {stats['escalation_rate']:.0%}, cache hits {stats['cache_hit_rate']:.0%}")


if __name__ == "__main__":
    main()
