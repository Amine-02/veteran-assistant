"""Run Q01-Q15 through the pipeline -> outputs/runs/<run_id>/.

Each run folder holds answers.json, answers.md and run.json (what produced it).
Use --repeat N to run several times: Claude answers vary between runs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.assistant.generate import SYSTEM_PROMPT
from src.assistant.pipeline import Assistant
from src.config import AS_OF, DATA_DIR, RUNS_DIR

GOLD = Path(__file__).resolve().parent / "gold.yaml"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _git_commit() -> str:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        return commit + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "none"


def run_once(bot: Assistant, questions: list[dict], personas: dict) -> list[dict]:
    results = []
    for q in questions:
        r = bot.ask(q["question"], personas.get(q["persona_id"]))
        results.append({"q_id": q["q_id"], "persona_id": q["persona_id"], **asdict(r)})
        print(f'  {q["q_id"]} {r.behavior:11} route={r.route:8} cites={r.citations}')
    return results


def run_metadata(run_id: str, results: list[dict]) -> dict:
    """What produced this run, so results can be compared and reproduced."""
    tokens: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for r in results:
        for k, v in r["usage"].items():
            tokens[r["model"]][k] += v
    gens = sorted({r["generator"] for r in results} - {"none"})
    return {
        "run_id": run_id,
        "generator": gens[0] if len(gens) == 1 else ",".join(gens) or "none",
        "as_of": AS_OF.isoformat(),
        "git_commit": _git_commit(),
        "system_prompt_sha": _sha(SYSTEM_PROMPT),
        "gold_sha": _sha(GOLD.read_text(encoding="utf-8")),
        "questions": len(results),
        "model_calls": sum(1 for r in results if r["model"]),
        "tokens_by_model": {m: dict(t) for m, t in tokens.items()},
        "total_latency_ms": sum(r["latency_ms"] for r in results),
    }


def answers_markdown(meta: dict, results: list[dict]) -> str:
    lines = [f"# Answers, run {meta['run_id']}", "",
             f"Generator: {meta['generator']} | commit: {meta['git_commit']} | "
             f"prompt: {meta['system_prompt_sha']} | gold: {meta['gold_sha']}", ""]
    for r in results:
        lines += [
            f"## {r['q_id']} ({r['persona_id']})",
            f"**Q:** {r['redacted_question']}", "",
            r["answer"], "",
            f"- behavior: {r['behavior']} | route: {r['route']} | model: {r['model'] or '-'}",
            f"- citations: {', '.join(r['citations']) or '-'} | retrieved: "
            f"{', '.join(r['retrieved_ids']) or '-'}",
            f"- profile fields used: {', '.join(r['profile_fields']) or 'none'}"
            f" | PII redacted: {', '.join(r['pii_types']) or 'none'}",
        ]
        if r["facts"]:
            lines.append(f"- computed facts: {r['facts']}")
        if r["check_failures"]:
            lines.append(f"- output check failures: {', '.join(r['check_failures'])}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=1, help="number of runs (default 1)")
    args = parser.parse_args()

    personas = {p["persona_id"]: p for p in json.loads(
        (DATA_DIR / "personas.json").read_text(encoding="utf-8"))["personas"]}
    with (DATA_DIR / "eval_questions.csv").open(encoding="utf-8") as f:
        questions = list(csv.DictReader(f))

    bot = Assistant()
    for i in range(args.repeat):
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        print(f"run {i + 1}/{args.repeat}")
        results = run_once(bot, questions, personas)

        meta = run_metadata("", results)
        run_id = f"{stamp}_{meta['generator']}"
        n = 2
        while (RUNS_DIR / run_id).exists():  # fast mock runs can share a second
            run_id = f"{stamp}_{meta['generator']}-{n}"
            n += 1
        meta["run_id"] = run_id
        out = RUNS_DIR / run_id
        out.mkdir(parents=True, exist_ok=True)
        (out / "answers.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        (out / "answers.md").write_text(answers_markdown(meta, results), encoding="utf-8")
        (out / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
