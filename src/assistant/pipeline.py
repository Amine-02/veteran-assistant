"""input -> guards -> retrieve -> router -> personalize -> generate -> output checks."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from src.assistant.generate import generate
from src.assistant.ingest import build
from src.assistant.input_guards import CRISIS_REPLY, DECLINES, REFUSE_REPLY, check_input
from src.assistant.output_checks import check_output
from src.assistant.pii import PII_WARNING, redact
from src.assistant.retrieve import WeightedBM25Retriever
from src.config import AS_OF, LOG_DIR

# Profile fields each topic may use (D23: only what is needed).
# Whole words only: "separating" must not match "rating", "eBenefits" must not match "benefits".
TOPIC_FIELDS = [
    (r"\b(gi bill|education|school|college|expire[sd]?|tuition)\b", ["separation_date", "branch"]),
    (r"\b(transfer\w*|daughters?|sons?|spouse|child(ren)?|family|dependents?)\b",
     ["separation_date", "dependents"]),
    (r"\b(home loans?|funding fee|mortgage|coe)\b", ["va_disability_rating"]),
    (r"\b(health|pact|burn pits?|toxic|exposure|agent orange|iraq|afghanistan)\b",
     ["deployments", "separation_date", "discharge"]),
    (r"\b(skillbridge|separat\w*|transition\w*|tap|jobs?|resume|careers?)\b",
     ["separation_date", "branch"]),
    (r"\b(state|property tax\w*|license plates?|tuition assistance)\b",
     ["state", "va_disability_rating"]),
    (r"\b(disability|rating|compensation)\b", ["va_disability_rating", "dependents"]),
    (r"\b(eligible|benefits?)\b", ["separation_date", "discharge", "va_disability_rating", "state"]),
]

FALLBACK = ("I couldn't produce a verified answer to that. Please check VA.gov, or ask a free "
            "VA-accredited representative for help [D19].")


@dataclass
class Result:
    question: str
    redacted_question: str
    behavior: str  # answer | not_covered | decline | crisis | refuse (+ pii_block flag)
    answer: str
    citations: list[str]
    route: str  # shortcut | S | M
    retrieved_ids: list[str] = field(default_factory=list)
    profile_fields: list[str] = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    pii_types: list[str] = field(default_factory=list)
    guard_reason: str = ""
    check_failures: list[str] = field(default_factory=list)
    generator: str = "none"
    model: str | None = None
    usage: dict = field(default_factory=dict)
    latency_ms: int = 0


def select_profile(question: str, persona: dict | None) -> dict | None:
    """Opt-in only, and only the fields the topic needs, plus derived date facts."""
    if not persona or not persona.get("personalization_opt_in"):
        return None
    wanted: list[str] = []
    for pattern, fields in TOPIC_FIELDS:
        if re.search(pattern, question, re.IGNORECASE):
            wanted += [f for f in fields if f not in wanted]
    profile = {f: persona[f] for f in wanted if persona.get(f) not in (None, [], "")}
    if "separation_date" in profile:
        days = (date.fromisoformat(profile["separation_date"]) - AS_OF).days
        profile["days_until_separation" if days >= 0 else "days_since_separation"] = abs(days)
    return profile or None


# "I left the Air Force in 2010", "got out in 2019", "separated in 2024".
SEPARATION_YEAR = re.compile(
    r"\b(left|got out|separated|discharged|retired|out of the \w+)\b[^.?!]{0,30}?"
    r"\b(19[5-9]\d|20[0-4]\d)\b",
    re.IGNORECASE,
)


def message_facts(text: str) -> dict:
    """Date math from what the user typed, done in code so the model doesn't have to.

    Only the year is known, so the range covers Jan 1 to Dec 31 of that year.
    Works without opt-in: it uses only the message itself (D23).
    """
    m = SEPARATION_YEAR.search(text)
    if not m:
        return {}
    year = int(m.group(2))
    if year > AS_OF.year:
        return {}
    low = (AS_OF - date(year, 12, 31)).days / 365.25
    high = (AS_OF - date(year, 1, 1)).days / 365.25
    return {
        "separation_year": year,
        "years_since_separation": f"between {low:.1f} and {high:.1f} (month not given)",
    }


def route(question: str, profile: dict | None, chunks) -> str:
    """Tier M for personalized or multi-doc questions, Tier S for simple FAQs."""
    if profile:
        return "M"
    docs = [c.metadata["doc_id"] for c in chunks]
    if len(set(docs[:2])) == 2 and chunks[1].metadata["score"] >= 0.6 * chunks[0].metadata["score"]:
        return "M"
    return "S"


class Assistant:
    def __init__(self, log_path: Path | None = LOG_DIR / "request_log.jsonl"):
        records, chunks = build()
        self.indexed_ids = {r.doc_id for r in records if r.status == "indexed"}
        self.retriever = WeightedBM25Retriever.from_documents(chunks, k=5)
        self.log_path = log_path

    def ask(self, question: str, persona: dict | None = None) -> Result:
        t0 = time.perf_counter()
        g = check_input(question)
        base = dict(question=question, redacted_question=g.clean_text,
                    pii_types=g.pii_types, guard_reason=g.reason)
        warn = PII_WARNING + " " if g.pii_types else ""

        if g.action == "crisis":
            res = Result(**base, behavior="crisis", answer=CRISIS_REPLY,
                         citations=["D12"], route="shortcut")
        elif g.action == "refuse":
            res = Result(**base, behavior="refuse", answer=warn + REFUSE_REPLY,
                         citations=[], route="shortcut")
        elif g.action == "decline":
            text, cites = DECLINES[g.reason]
            res = Result(**base, behavior="decline", answer=warn + text,
                         citations=cites, route="shortcut")
        else:
            res = self._answer(g.clean_text, persona, base, warn)

        res.latency_ms = int((time.perf_counter() - t0) * 1000)
        self._log(res, persona)
        return res

    def _answer(self, text: str, persona: dict | None, base: dict, warn: str) -> Result:
        chunks = self.retriever.invoke(text)
        retrieved = list(dict.fromkeys(c.metadata["doc_id"] for c in chunks))
        profile = select_profile(text, persona)
        tier = route(text, profile, chunks) if len(chunks) >= 2 else ("M" if profile else "S")

        facts = message_facts(text)
        gen = generate(text, chunks, profile, AS_OF.isoformat(), tier, facts)
        failures = check_output(gen.answer, gen.citations, retrieved, self.indexed_ids)

        answer, cites = gen.answer, gen.citations
        behavior = "not_covered" if gen.not_covered else "answer"
        if failures:
            answer, cites, behavior = FALLBACK, ["D19"], "not_covered"
        elif behavior == "answer" and not cites:
            failures.append("answer_without_citation")
            answer, cites, behavior = FALLBACK, ["D19"], "not_covered"

        return Result(**base, behavior=behavior, answer=warn + answer, citations=cites,
                      route=tier, retrieved_ids=retrieved,
                      profile_fields=sorted(profile) if profile else [], facts=facts,
                      check_failures=failures, generator=gen.generator, model=gen.model,
                      usage=gen.usage)

    def _log(self, res: Result, persona: dict | None) -> None:
        """Redacted log only: the raw question is never written (D23)."""
        if not self.log_path:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        row = asdict(res)
        row.pop("question")
        row["answer"], _ = redact(row["answer"])
        row["persona_id"] = persona.get("persona_id") if persona else None
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
