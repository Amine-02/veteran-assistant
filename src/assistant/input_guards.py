"""Input guards, run before retrieval and before the model.

All rules are regexes so they are fast, free and auditable. Production would
add a small classifier for the unclear cases, never remove these.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.assistant.pii import redact

# ---------------------------------------------------------------- crisis
CRISIS = re.compile(
    r"\b(suicid\w*|kill(ing)? (my|him|her|them)sel(f|ves)|end(ing)? (it|it all|my life)"
    r"|want(ed)? to die|better off dead|no reason to live|self[- ]?harm"
    r"|(don'?t|do not|can'?t) see the point( of (anything|living|life))?"
    r"|hurt(ing)? myself|crisis lin\w*"
    r"|nobody (would|will|'?d) miss me|(i'?m|i am) not ok(ay)?|end it all)\b",
    re.IGNORECASE,
)

# Facts from D12. The citation is kept in Result.citations, not shown to the user.
CRISIS_REPLY = (
    "I'm really sorry you're going through this. You don't have to face it alone. "
    "Free, confidential support is available 24/7 from the Veterans Crisis Line: "
    "dial 988 and then press 1, text 838255, or chat online at VeteransCrisisLine.net. "
    "Family and friends can use these services too. "
    "If you or someone else is in immediate danger, call 911."
)

# ---------------------------------------------------------------- injection / junk
INJECTION = re.compile(
    r"ignore (all )?(of )?(your |the )?(previous|prior|above) (instructions|rules)"
    r"|(reveal|print|show) (me )?(your )?(system prompt|hidden rules|instructions)"
    r"|you are now\b|\bDAN\b|jailbreak|developer mode|\bsudo\b|admin access"
    r"|<\s*script|javascript:|\bdrop table\b",
    re.IGNORECASE,
)
SPAM = re.compile(
    r"\b(bitcoin|crypto|nft|followers|casino|viagra|forex|giveaway|click here|buy now)\b",
    re.IGNORECASE,
)
VOWEL = re.compile(r"[aeiouy]")

REFUSE_REPLY = (
    "I can only help with questions about veteran benefits, transition, jobs and daily "
    "life. Could you rephrase your question?"
)

# ---------------------------------------------------------------- out of scope
CLAIM_LOOKUP = re.compile(
    r"\b(can|could|will|would) you\b.{0,40}\b(look ?up|check|pull up|find|access|see|update)\b"
    r".{0,30}\b(my|the) (claim|account|records?|file|status|appeal)"
    r"|\b(check|look ?up|pull up) my (claim|account|records?|file|appeal)\b"
    r"|\[REDACTED_(SSN|VA_FILE_NUMBER)\].{0,40}\b(status|claim)\b",
    re.IGNORECASE,
)
# "How do I check my claim status?" is a how-to question, not a lookup request (Q07).
HOW_TO = re.compile(r"\b(how|where) (do|can|should|would) i\b", re.IGNORECASE)
OUTCOME = re.compile(
    r"\b(will|would|going to)\b.{0,40}\b(get )?(approved|denied|accepted|granted)"
    r"|what (rating|percent(age)?) (will|would|should|do) i get"
    r"|(chances|odds) (of|that).{0,30}(claim|approved|appeal)",
    re.IGNORECASE,
)
LEGAL = re.compile(r"\b(lawyer|attorney|sue|lawsuit|legal advice)\b", re.IGNORECASE)
MEDICAL = re.compile(
    r"\b(dosage|dose|should i (take|stop taking)|diagnos(e|is) me|is it (cancer|serious)"
    r"|what medication)\b",
    re.IGNORECASE,
)

DECLINES = {
    "claim_lookup": (
        "I can't access VA accounts or look up claims [D23]. You can check your claim "
        "status yourself by signing in to VA.gov with Login.gov or ID.me and opening your "
        "claim status page [D06]. A free VA-accredited representative can also help "
        "with your claim [D19].",
        ["D23", "D06", "D19"],
    ),
    "outcome_prediction": (
        "I can't predict whether a claim will be approved or what rating VA will assign. "
        "VA decides the rating from the evidence in your claim [D05]. For help building "
        "your claim, a Veterans Service Organization or other VA-accredited representative "
        "can help at no cost, and you can search for one on VA.gov [D19].",
        ["D05", "D19"],
    ),
    "legal": (
        "I can't give legal advice. For help with a VA claim, VA-accredited representatives "
        "and Veterans Service Organizations help at no cost, and it is against the law to "
        "charge you for help with an initial claim [D19].",
        ["D19"],
    ),
    "medical": (
        "I can't give medical advice. Please talk to your health care provider. If you are "
        "enrolled in VA health care, your VA care team can help [D08].",
        ["D08"],
    ),
}


@dataclass
class GuardResult:
    clean_text: str
    action: str = "continue"  # continue | crisis | refuse | decline
    reason: str = ""
    pii_types: list[str] = field(default_factory=list)


def is_gibberish(text: str) -> bool:
    if not re.search(r"[a-z0-9]", text.lower()):
        return True
    words = [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4]
    if not words:
        return False
    bad = [w for w in words if not VOWEL.search(w) or re.search(r"[^aeiouy\W]{5,}", w)
           or re.search(r"(\w)\1{3,}", w)]
    return len(bad) / len(words) > 0.5


def check_input(text: str) -> GuardResult:
    # 1. Redact first, so nothing downstream (logs, model) sees raw PII.
    clean, pii = redact(text)
    result = GuardResult(clean_text=clean, pii_types=pii)

    # 2. Crisis wins over everything else.
    if CRISIS.search(clean):
        result.action, result.reason = "crisis", "crisis_language"
        return result
    if INJECTION.search(clean):
        result.action, result.reason = "refuse", "injection"
        return result
    if SPAM.search(clean) or is_gibberish(clean):
        result.action, result.reason = "refuse", "junk"
        return result
    for reason, pattern in (("claim_lookup", CLAIM_LOOKUP), ("outcome_prediction", OUTCOME),
                            ("legal", LEGAL), ("medical", MEDICAL)):
        if pattern.search(clean):
            if reason == "claim_lookup" and HOW_TO.search(clean):
                continue
            result.action, result.reason = "decline", reason
            return result
    return result
