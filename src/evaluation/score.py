"""Score every run in outputs/runs/ against gold.yaml.

Writes scores.md + scores.json inside each run folder, and outputs/runs/summary.md
with a headline per generator, a pass rate per question and the reasons for failures.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from src.config import RUNS_DIR

HERE = Path(__file__).resolve().parent
EXCLUDED = {"D03", "D07", "D11", "D20", "D22"}
CHECKS = {
    "behavior_ok": "right type of reply (answer, not covered, decline, crisis, refuse)",
    "cites_ok": "cites the docs it must cite",
    "no_bad_cite": "never cites or retrieves an excluded doc (D03, D07, D11, D20, D22)",
    "includes_ok": "contains the required content",
    "excludes_ok": "contains no forbidden content",
    "retrieval_hit": "the expected doc was retrieved",
    "pii_ok": "PII redacted and the user warned (Q13)",
    "profile_ok": "only allowed profile fields were sent to the model (D23)",
}


def md(text: str) -> str:
    """Escape '|' so regexes don't break markdown table columns."""
    return text.replace("|", r"\|")


def score_one(ans: dict, gold: dict) -> dict:
    text = ans["answer"]
    expected = gold["behavior"] if isinstance(gold["behavior"], list) else [gold["behavior"]]
    cites, retrieved = set(ans["citations"]), set(ans["retrieved_ids"])
    profile_allowed = set(gold.get("profile_allowed", ans["profile_fields"]))
    misses = [p for p in gold.get("must_include", []) if not re.search(p, text, re.I)]
    hits = [p for p in gold.get("must_not_include", []) if re.search(p, text, re.I)]

    out = {
        "behavior_ok": ans["behavior"] in expected,
        "cites_ok": set(gold.get("must_cite", [])) <= cites,
        "no_bad_cite": not ((cites | retrieved) & EXCLUDED),
        "includes_ok": not misses,
        "excludes_ok": not hits,
        "retrieval_hit": set(gold.get("must_retrieve", [])) <= retrieved,
        "pii_ok": bool(ans["pii_types"]) and "[D23]" in text if gold.get("pii") else True,
        "profile_ok": set(ans["profile_fields"]) <= profile_allowed,
    }
    out["pass"] = all(out[c] for c in CHECKS)

    # Plain-language reasons, one per failed check.
    reasons = []
    if not out["behavior_ok"]:
        reasons.append(f"replied '{ans['behavior']}', expected '{' or '.join(expected)}'")
    if not out["cites_ok"]:
        reasons.append(f"did not cite {', '.join(sorted(set(gold['must_cite']) - cites))}")
    if not out["no_bad_cite"]:
        reasons.append(f"used excluded doc {', '.join(sorted((cites | retrieved) & EXCLUDED))}")
    reasons += [f"missing /{p}/" for p in misses]
    reasons += [f"contains forbidden /{p}/" for p in hits]
    if not out["retrieval_hit"]:
        reasons.append(f"did not retrieve {', '.join(sorted(set(gold['must_retrieve']) - retrieved))}")
    if not out["pii_ok"]:
        reasons.append("PII not redacted or no warning")
    if not out["profile_ok"]:
        extra = sorted(set(ans["profile_fields"]) - profile_allowed)
        reasons.append(f"sent profile fields it should not: {', '.join(extra)}")
    out["reasons"] = reasons
    return out


def score_run(run_dir: Path, gold: dict) -> dict:
    answers = json.loads((run_dir / "answers.json").read_text(encoding="utf-8"))
    meta_path = run_dir / "run.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    scores = {a["q_id"]: {"behavior": a["behavior"], **score_one(a, gold[a["q_id"]])}
              for a in answers}

    n = len(scores)
    passed = sum(s["pass"] for s in scores.values())
    lines = [f"# Scores, run {run_dir.name}", "",
             f"Generator: {meta.get('generator', '?')} | gold: {meta.get('gold_sha', '?')}", "",
             f"**Passed {passed}/{n}**", "",
             "| Q | about | behavior | " + " | ".join(CHECKS) + " | pass | why it failed |",
             "|---" * (len(CHECKS) + 5) + "|"]
    for q, s in scores.items():
        marks = " | ".join("Y" if s[c] else "N" for c in CHECKS)
        lines.append(f"| {q} | {gold[q].get('about', '')} | {s['behavior']} | {marks} | "
                     f"{'Y' if s['pass'] else 'N'} | {md('; '.join(s['reasons']))} |")
    (run_dir / "scores.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (run_dir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    return {"run_id": run_dir.name, "generator": meta.get("generator", "?"),
            "prompt": meta.get("system_prompt_sha", "?"), "gold_sha": meta.get("gold_sha", "?"),
            "passed": passed, "n": n, "scores": scores}


def summary_markdown(runs: list[dict], gold: dict, gold_sha: str) -> str:
    # Runs are pooled only if they share a generator and a system prompt.
    # Groups keep the order of their first run, so older versions come first.
    by_gen: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        by_gen[f"{r['generator']} {r['prompt'][:6]}"].append(r)
    gens = list(by_gen)
    questions = list(runs[0]["scores"])

    lines = ["# Eval summary", "",
             "Each run answers the 15 eval questions once. A question passes only if every "
             "check passes. Claude answers vary between runs, so the pass rate over several "
             "runs is the number to report.", "",
             "Runs are grouped by generator and system prompt version (the 6-character hash). "
             f"All runs are scored with the current gold.yaml ({gold_sha}).", ""]

    # 1. Headline
    lines += ["## Headline", "", "| version | runs | passed per run | average |",
              "|---|---|---|---|"]
    for g in gens:
        counts = [r["passed"] for r in by_gen[g]]
        n = by_gen[g][0]["n"]
        lines.append(f"| {g} | {len(counts)} | {', '.join(f'{c}/{n}' for c in counts)} | "
                     f"{sum(counts) / len(counts):.1f}/{n} |")

    # 2. Per question
    lines += ["", "## Per question", "",
              "Cells show how many runs passed. Reasons are counted over all runs.", "",
              "| Q | what it tests | " + " | ".join(gens) + " | why it failed |",
              "|---" * (len(gens) + 3) + "|"]
    for q in questions:
        cells = []
        why = []
        for g in gens:
            gr = by_gen[g]
            ok = sum(r["scores"][q]["pass"] for r in gr)
            cells.append(f"{ok}/{len(gr)}" + ("" if ok == len(gr) else " ✗"))
            reasons = Counter(x for r in gr for x in r["scores"][q]["reasons"])
            why += [f"{g}: {x}" + (f" ({k}×)" if k > 1 else "") for x, k in reasons.items()]
        lines.append(f"| {q} | {gold[q].get('about', '')} | {' | '.join(cells)} | "
                     f"{md('<br>'.join(why)) or '-'} |")

    # 3. Runs
    lines += ["", "## Runs", "",
              "| run | version | passed | failed questions |",
              "|---|---|---|---|"]
    for r in runs:
        failed = [q for q, s in r["scores"].items() if not s["pass"]]
        lines.append(f"| {r['run_id']} | {r['generator']} {r['prompt'][:6]} | "
                     f"{r['passed']}/{r['n']} | {', '.join(failed) or '-'} |")

    # 4. Legend
    lines += ["", "## What each check means", ""]
    lines += [f"- `{c}`: {d}" for c, d in CHECKS.items()]
    lines += ["", "Details for one run, check by check: `<run>/scores.md`."]
    return "\n".join(lines) + "\n"


def main() -> None:
    gold_text = (HERE / "gold.yaml").read_text(encoding="utf-8")
    gold = yaml.safe_load(gold_text)
    gold_sha = hashlib.sha256(gold_text.encode()).hexdigest()[:12]
    run_dirs = sorted(d for d in RUNS_DIR.glob("*") if (d / "answers.json").exists())
    if not run_dirs:
        print(f"No runs in {RUNS_DIR}. Run src.evaluation.run_eval first.")
        return
    runs = [score_run(d, gold) for d in run_dirs]
    (RUNS_DIR / "summary.md").write_text(summary_markdown(runs, gold, gold_sha), encoding="utf-8")
    for r in runs:
        print(f"{r['run_id']}: {r['passed']}/{r['n']}")
    print(f"wrote {RUNS_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
