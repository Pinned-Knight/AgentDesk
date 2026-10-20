"""Input guardrails: mask payment-card numbers and flag prompt-injection attempts."""

import re
from dataclasses import dataclass, field

REFUSAL = "I can't help with that request, but I'm happy to help with orders, returns, and store policies."

_CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_INJECTION = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+|any\s+|your\s+|the\s+)*(previous|prior|above|earlier|system)\s+"
    r"(instructions?|prompts?|rules?|messages?)"
    r"|(reveal|show|print|repeat|leak)\s+(me\s+)?(your\s+|the\s+)*(system\s+)?(prompt|instructions)"
    r"|you\s+are\s+now\s+(dan|an?\s+unrestricted)|developer\s+mode|jailbreak",
    re.I,
)


@dataclass
class GuardrailResult:
    clean_message: str
    flags: list[str] = field(default_factory=list)


def _luhn_ok(digits: str) -> bool:
    total, double = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        double = not double
    return total % 10 == 0


def mask_cards(text: str) -> tuple[str, bool]:
    found = False

    def repl(m: re.Match) -> str:
        nonlocal found
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            found = True
            return "[card]"
        return m.group(0)

    return _CARD_CANDIDATE.sub(repl, text), found


def check_input(message: str) -> GuardrailResult:
    clean, masked = mask_cards(message)
    flags = []
    if masked:
        flags.append("pii_masked")
    if _INJECTION.search(clean):
        flags.append("prompt_injection")
    return GuardrailResult(clean_message=clean, flags=flags)
