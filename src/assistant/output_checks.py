"""Output checks, run on the model's answer before it is shown."""

from __future__ import annotations

import re

from src.assistant.pii import redact

URL = re.compile(r"\b(?:https?://)?(?:[\w-]+\.)+(?:com|net|org|gov|mil|biz|io|info|us)\b(?:/\S*)?",
                 re.IGNORECASE)
ALLOWED_DOMAINS = ("va.gov", "veteranscrisisline.net", "military.com", "login.gov",
                   "id.me", "dmdc.osd.mil", "dodskillbridge.usalearning.gov")


def _domain_allowed(url: str) -> bool:
    host = re.sub(r"^https?://", "", url.lower()).split("/")[0]
    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)


def check_output(answer: str, citations: list[str], retrieved_ids: list[str],
                 indexed_ids: set[str]) -> list[str]:
    """Return a list of failures. Empty list means the answer can be shown."""
    failures = []
    for c in citations:
        if c not in indexed_ids:
            failures.append(f"citation_not_indexed:{c}")
        elif c not in retrieved_ids:
            failures.append(f"citation_not_retrieved:{c}")
    inline = set(re.findall(r"\[(D\d{2})\]", answer))
    for c in inline - set(citations):
        failures.append(f"inline_citation_not_listed:{c}")
    _, pii = redact(answer)
    failures += [f"pii_in_output:{p}" for p in pii]
    failures += [f"url_not_allowed:{u}" for u in URL.findall(answer) if not _domain_allowed(u)]
    return failures
