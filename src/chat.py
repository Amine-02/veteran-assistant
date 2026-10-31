"""Ask the assistant your own questions from the terminal.

    uv run python -m src.chat                # as a guest (no profile)
    uv run python -m src.chat --persona P1   # as a persona from data/personas.json

Each question goes through the same pipeline as the eval. Questions are answered
one at a time: the assistant does not remember earlier turns.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap

from src.assistant.pipeline import Assistant
from src.config import DATA_DIR


def load_personas() -> dict:
    data = json.loads((DATA_DIR / "personas.json").read_text(encoding="utf-8"))
    return {p["persona_id"]: p for p in data["personas"]}


def describe(persona: dict | None) -> str:
    if not persona:
        return "guest, no profile"
    opt = "opted in" if persona.get("personalization_opt_in") else "opted out"
    return f"{persona['persona_id']} {persona['display_name']}, {opt}"


def details(r) -> str:
    parts = [f"behavior: {r.behavior}", f"route: {r.route}"]
    if r.model:
        parts.append(f"model: {r.model}")
    parts.append(f"cites: {', '.join(r.citations) or '-'}")
    if r.retrieved_ids:
        parts.append(f"retrieved: {', '.join(r.retrieved_ids)}")
    if r.profile_fields:
        parts.append(f"profile: {', '.join(r.profile_fields)}")
    if r.facts:
        parts.append(f"facts: {r.facts}")
    if r.pii_types:
        parts.append(f"PII redacted: {', '.join(r.pii_types)}")
    if r.guard_reason:
        parts.append(f"guard: {r.guard_reason}")
    if r.check_failures:
        parts.append(f"check failures: {', '.join(r.check_failures)}")
    parts.append(f"{r.latency_ms} ms")
    return " | ".join(parts)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--persona", help="persona id, e.g. P1 (default: guest)")
    args = parser.parse_args()

    personas = load_personas()
    persona = None
    if args.persona:
        persona = personas.get(args.persona.upper())
        if not persona:
            parser.error(f"unknown persona {args.persona}. Choose from {', '.join(personas)}")

    generator = "Claude" if os.environ.get("ANTHROPIC_API_KEY") else "mock (no ANTHROPIC_API_KEY)"
    print(f"Veteran assistant | as: {describe(persona)} | generator: {generator}")
    print("Type a question. Empty line or 'quit' to exit.\n")

    bot = Assistant()
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in ("", "quit", "exit"):
            break
        r = bot.ask(question, persona)
        print()
        print(textwrap.fill(r.answer, width=90))
        print(textwrap.fill(f"[{details(r)}]", width=90, subsequent_indent=" "))
        print()


if __name__ == "__main__":
    main()
