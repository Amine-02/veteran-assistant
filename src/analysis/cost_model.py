"""C3: monthly model spend for the plan vs two baselines -> outputs/analysis/cost_model.md.

Uses the brief's assumed prices and token profile. Traffic shares come from
traffic_mix.json (run src.analysis.traffic_mix first). Every number is printed
with its arithmetic so it can be checked by hand.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter

from src.analysis.traffic_mix import intent_key
from src.config import ANALYSIS_DIR

TURNS = 40_000 * 3 * 4  # MAU x sessions x turns = 480,000
BUDGET = 3_500

# Brief prices, $ per 1M tokens. Cached input = 10% of the tier's input price.
PRICE = {"S": (0.25, 1.25), "M": (3.00, 15.00), "L": (15.00, 75.00)}
EMBED = 0.10
CACHE_RATE = 0.10

# Brief token profile of one full-path turn.
BRIEF = {"cached": 900, "history": 600, "retrieved": 5 * 350, "user": 60, "output": 250}
# Measured in the prototype (Claude runs, prompt 3c225d): ~850 cached system prompt,
# ~1,150 other input (5 short chunks + profile + question), ~180 output, no history.
# Production adds the brief's 600 history tokens.
MEASURED = {"cached": 850, "history": 600, "retrieved": 1_090, "user": 60, "output": 180}

# Safety + routing classifier (Tier S) on every turn the regex guards let through.
CLASSIFIER = {"cached": 250, "history": 0, "retrieved": 0, "user": 60, "output": 10}
QUERY_EMBED_TOKENS = 80
CORPUS_TOKENS = 20_000 * 1_200  # 24M
REFRESH = 0.10

# Offline evaluation: Tier L judge on a 0.5% sample of live turns + eval set reruns.
JUDGE_SAMPLE = 0.005
JUDGE = {"cached": 0, "history": 0, "retrieved": 3_310, "user": 250, "output": 200}

# Share of Tier S answers that fail output checks and are retried on Tier M.
ESCALATION = 0.05

# Optional Tier S re-ranker (not in the plan): scores 5 chunks + the question.
RERANK = {"cached": 0, "history": 0, "retrieved": 5 * 350, "user": 60, "output": 20}


def turn_cost(profile: dict, tier: str) -> float:
    inp, out = PRICE[tier]
    uncached = profile["history"] + profile["retrieved"] + profile["user"]
    return (profile["cached"] * inp * CACHE_RATE + uncached * inp + profile["output"] * out) / 1e6


def turn_formula(profile: dict, tier: str) -> str:
    inp, out = PRICE[tier]
    uncached = profile["history"] + profile["retrieved"] + profile["user"]
    return (f"({profile['cached']:,} × ${inp * CACHE_RATE:.3f} + {uncached:,} × ${inp:.2f} + "
            f"{profile['output']} × ${out:.2f}) / 1M = ${turn_cost(profile, tier):.6f}")


def plan(shares: dict, route: dict, profile: dict, turns: int) -> dict:
    """Monthly cost of each line of the plan."""
    s = sum(v for k, v in shares.items() if route[k] == "S")
    m = sum(v for k, v in shares.items() if route[k] == "M")
    reaches_model = s + m
    lines = {
        "Tier S answers (simple FAQ)": turns * s * turn_cost(profile, "S"),
        "Tier M answers (personalized / multi-step)": turns * m * turn_cost(profile, "M"),
        f"Tier M retries ({ESCALATION:.0%} of Tier S answers)":
            turns * s * ESCALATION * turn_cost(profile, "M"),
        "Tier S safety + routing classifier": turns * reaches_model * turn_cost(CLASSIFIER, "S"),
        "Query embeddings": turns * reaches_model * QUERY_EMBED_TOKENS * EMBED / 1e6,
        "Corpus refresh embeddings (10%/month)": CORPUS_TOKENS * REFRESH * EMBED / 1e6,
        f"Offline eval, Tier L judge on {JUDGE_SAMPLE:.1%} of turns":
            turns * JUDGE_SAMPLE * turn_cost(JUDGE, "L"),
    }
    lines["Total"] = sum(lines.values())
    return lines


def faq_concentration() -> tuple[int, float]:
    """Share of simple-FAQ queries covered by the 100 most common intents."""
    path = ANALYSIS_DIR / "traffic_mix.csv"
    rows = [r for r in csv.DictReader(path.open(encoding="utf-8")) if r["category"] == "simple_faq"]
    norm = Counter(intent_key(r["redacted"]) for r in rows)
    top = sum(k for _, k in norm.most_common(100))
    return len(norm), top / len(rows)


def safety_evidence() -> str:
    """How many sensitive queries each labeler caught (rules, Haiku, either)."""
    rows = list(csv.DictReader((ANALYSIS_DIR / "traffic_mix.csv").open(encoding="utf-8")))
    if "llm_category" not in rows[0]:
        return "Run the traffic mix with Haiku to compare the two safety layers."
    rules = {i for i, r in enumerate(rows) if r["category"] == "sensitive"}
    llm = {i for i, r in enumerate(rows) if r["llm_category"] == "sensitive"}
    return (f"On the search queries, rules flagged {len(rules)} sensitive queries, Haiku "
            f"{len(llm)}, either {len(rules | llm)}. Haiku caught {len(llm - rules)} the rules "
            f"missed, the rules caught {len(rules - llm)} Haiku missed.")


# Short labels for the terminal summary, one per C2 stage.
C2_SHORT = {
    "Safety checks": "regex + Tier S classifier",
    "Routing": "same Tier S call",
    "Embeddings": "embedding model + BM25",
    "Re-ranking": "none at launch",
    "Answer generation": "Tier S FAQ, Tier M personalized",
    "Offline evaluation": "rules + Tier L judge on a sample",
}


def c2_section(p: dict, s: float, m: float) -> tuple[list[str], list[tuple], float]:
    """C2: one row per stage the brief lists, with tier, reason and monthly cost.

    Returns the markdown lines, the rows (stage, choice, why, arithmetic, cost)
    and the cost of the optional re-ranker.
    """
    reach = TURNS * (s + m)
    rerank = reach * turn_cost(RERANK, "S")
    judge = next(v for k, v in p.items() if k.startswith("Offline eval"))
    retries = next(v for k, v in p.items() if k.startswith("Tier M retries"))
    embeds = p["Query embeddings"] + p["Corpus refresh embeddings (10%/month)"]
    rows = [
        ("Safety checks", "Regex (no model), then Tier S classifier on every turn that passes",
         "Regex is instant and auditable. The classifier catches typos and rephrasing. "
         "Crisis replies are fixed text, never generated. " + safety_evidence(),
         f"{reach:,.0f} turns × ${turn_cost(CLASSIFIER, 'S'):.6f}",
         p["Tier S safety + routing classifier"]),
        ("Routing", "Same Tier S call returns the category",
         "No extra call. Routing on the question itself, not on retrieval scores.",
         "included above", 0.0),
        ("Embeddings", "Embedding model ($0.10 / 1M), hybrid with BM25",
         "Finds paraphrases keyword search misses once the corpus is 20,000 docs.",
         f"{reach:,.0f} × 80 tokens + 2.4M refresh tokens, × $0.10 / 1M", embeds),
        ("Re-ranking", "None at launch",
         "Trust × freshness weighting in code ranks official, recent docs first. "
         "Add a Tier S re-ranker only if the retrieval hit rate drops.",
         f"option: {reach:,.0f} × ${turn_cost(RERANK, 'S'):.6f}", 0.0),
        ("Answer generation", "Tier S for simple FAQ, Tier M for personalized or multi-step, "
         "Tier M retry when Tier S fails output checks",
         "Most traffic is simple FAQ. Tier M only where reasoning over the user's facts "
         "or several docs is needed. Tier L never answers users.",
         f"S {money(p['Tier S answers (simple FAQ)'])} + "
         f"M {money(p['Tier M answers (personalized / multi-step)'])} + retries {money(retries)}",
         p["Tier S answers (simple FAQ)"] + p["Tier M answers (personalized / multi-step)"]
         + retries),
        ("Offline evaluation", "Rule checks on the eval set (free) + Tier L judge on a sample",
         "Rule checks catch wrong behavior, citations and PII but not unsupported details. "
         "A strong judge checks each claim against the cited text.",
         f"{TURNS * JUDGE_SAMPLE:,.0f} turns × ${turn_cost(JUDGE, 'L'):.4f}", judge),
    ]
    out = ["# C2 model choice per stage", "",
           "One row per stage the brief lists. Costs use the brief's prices and the C1 "
           "traffic mix, and add up to the plan total in `cost_model.md`.", "",
           "| stage | choice | why | arithmetic | $ / month |", "|---|---|---|---|---|"]
    for stage, choice, why, arith, cost in rows:
        out.append(f"| {stage} | {choice} | {why} | {arith} | {money(cost)} |")
    total = sum(r[4] for r in rows)
    out += ["", f"Total: {money(total)} / month.",
            f"The optional Tier S re-ranker would add {money(rerank)} / month "
            f"({money(total)} → {money(total + rerank)}).",
            "", "Tier mapping used in the prototype: Tier S = Claude Haiku 5.5, Tier M = Claude "
            "Sonnet 5.5. Tier L is not used in the live path."]
    return out, rows, rerank


def money(x: float) -> str:
    return f"${x:,.0f}" if x >= 10 else f"${x:,.2f}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    mix = json.loads((ANALYSIS_DIR / "traffic_mix.json").read_text(encoding="utf-8"))
    shares, route = mix["shares"], mix["route"]
    s = sum(v for k, v in shares.items() if route[k] == "S")
    m = sum(v for k, v in shares.items() if route[k] == "M")
    none = 1 - s - m
    embed_all = TURNS * QUERY_EMBED_TOKENS * EMBED / 1e6 + CORPUS_TOKENS * REFRESH * EMBED / 1e6

    out = ["# C3 cost model", "",
           f"Turns per month: 40,000 × 3 × 4 = {TURNS:,}. Budget: ${BUDGET:,} for model + embeddings.",
           "Prices and token profile are the brief's assumptions.", "",
           "## Cost of one turn (brief profile)", "",
           "Input = 900 cached system prompt + 600 history + 1,750 retrieved + 60 user. Output 250.", ""]
    for t in "SML":
        out.append(f"- Tier {t}: {turn_formula(BRIEF, t)}")
    out.append(f"- Classifier call (Tier S): {turn_formula(CLASSIFIER, 'S')}")

    out += ["", "## Traffic mix used (from C1)", "",
            f"- Tier S (simple FAQ): {s:.1%}",
            f"- Tier M (personalized / multi-step): {m:.1%}",
            f"- No model call (crisis, PII lookups, out of scope, junk): {none:.1%}", ""]

    # Baselines: every turn on one tier, no guards or routing.
    out += ["## Baselines", "", "| baseline | per turn | model | embeddings | total / month | fits? |",
            "|---|---|---|---|---|---|"]
    for t in "ML":
        model = TURNS * turn_cost(BRIEF, t)
        total = model + embed_all
        out.append(f"| everything on Tier {t} | ${turn_cost(BRIEF, t):.5f} | {money(model)} | "
                   f"{money(embed_all)} | **{money(total)}** | {'yes' if total <= BUDGET else 'no'} |")

    # The plan.
    p = plan(shares, route, BRIEF, TURNS)
    out += ["", "## Plan (brief token profile)", "", "| line | arithmetic | $ / month |", "|---|---|---|"]
    notes = {
        "Tier S answers (simple FAQ)": f"{TURNS:,} × {s:.1%} × ${turn_cost(BRIEF, 'S'):.6f}",
        "Tier M answers (personalized / multi-step)": f"{TURNS:,} × {m:.1%} × ${turn_cost(BRIEF, 'M'):.5f}",
        f"Tier M retries ({ESCALATION:.0%} of Tier S answers)":
            f"{TURNS:,} × {s:.1%} × {ESCALATION:.0%} × ${turn_cost(BRIEF, 'M'):.5f}",
        "Tier S safety + routing classifier": f"{TURNS:,} × {s + m:.1%} × ${turn_cost(CLASSIFIER, 'S'):.6f}",
        "Query embeddings": f"{TURNS:,} × {s + m:.1%} × 80 tokens × $0.10 / 1M",
        "Corpus refresh embeddings (10%/month)": "24M tokens × 10% × $0.10 / 1M",
        f"Offline eval, Tier L judge on {JUDGE_SAMPLE:.1%} of turns":
            f"{TURNS:,} × {JUDGE_SAMPLE:.1%} × ${turn_cost(JUDGE, 'L'):.4f}",
    }
    for k, v in p.items():
        if k == "Total":
            out.append(f"| **Total** | | **{money(v)}** |")
        else:
            out.append(f"| {k} | {notes[k]} | {money(v)} |")
    out += ["", f"One-time: embedding the full corpus = 24M × $0.10 / 1M = "
                f"{money(CORPUS_TOKENS * EMBED / 1e6)}.",
            f"The plan uses {p['Total'] / BUDGET:.0%} of the budget, "
            f"{p['Total'] / (TURNS * turn_cost(BRIEF, 'M') + embed_all):.0%} of the all-Tier-M baseline."]

    c2_lines, c2_rows, rerank = c2_section(p, s, m)
    (ANALYSIS_DIR / "model_choices.md").write_text("\n".join(c2_lines) + "\n", encoding="utf-8")
    out += ["", "The tier chosen for each stage, and why, is in `model_choices.md` (C2)."]

    # Sensitivity.
    out += ["", "## What could break the budget", "",
            "Search queries are short, single questions with no persona. Chat turns 2-4 are "
            "follow-ups that are more often personalized, so the Tier M share is probably "
            "higher in chat. The table moves traffic from Tier S to Tier M.", "",
            "| Tier M share | 480k turns | 960k turns (usage doubles) |", "|---|---|---|"]
    for m_share in (m, 0.20, 0.30, 0.50):
        sh = {"simple_faq": s + m - m_share, "personalized": m_share,
              **{k: v for k, v in shares.items() if route[k] == "none"}}
        a = plan(sh, route, BRIEF, TURNS)["Total"]
        b = plan(sh, route, BRIEF, 2 * TURNS)["Total"]
        label = f"{m_share:.1%} (measured)" if m_share == m else f"{m_share:.0%}"
        out.append(f"| {label} | {money(a)} | {money(b)} |")
    # Break-even Tier M share at 480k and 960k turns (cost is linear in the M share).
    break_even = {}
    for turns in (TURNS, 2 * TURNS):
        def cost(x):
            return plan({"simple_faq": s + m - x, "personalized": x,
                         **{k: v for k, v in shares.items() if route[k] == "none"}},
                        route, BRIEF, turns)["Total"]
        c0, c1 = cost(0), cost(1)
        break_even[turns] = (BUDGET - c0) / (c1 - c0)
        out.append(f"\nAt {turns:,} turns the plan stays under ${BUDGET:,} while the Tier M share "
                   f"is below {break_even[turns]:.0%}.")

    # Measured profile.
    pm = plan(shares, route, MEASURED, TURNS)
    out += ["", "## Same plan with the measured token profile", "",
            "The prototype measured ~850 cached + ~1,150 other input and ~180 output per call "
            "(short pack chunks, no history). Adding 600 history tokens:", "",
            f"- Tier S turn: {turn_formula(MEASURED, 'S')}",
            f"- Tier M turn: {turn_formula(MEASURED, 'M')}",
            f"- Plan total: **{money(pm['Total'])}** / month (vs {money(p['Total'])} with the "
            "brief profile). Real articles are longer than the pack excerpts, so the brief "
            "profile is the safer number."]

    n_intents, top100 = faq_concentration()
    out += ["", "## Answer cache potential", "",
            f"Simple FAQ traffic has {n_intents:,} distinct questions once prefixes and typos are merged. "
            f"The 100 most common cover {top100:.0%} of simple-FAQ queries. A cache of reviewed "
            "answers for these (invalidated on each index version) would cut most Tier S "
            "calls. Search-box text repeats more than chat does, so treat this as an upper bound."]

    (ANALYSIS_DIR / "cost_model.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    # Short terminal summary. The full report with all arithmetic is in the .md file.
    base_m = TURNS * turn_cost(BRIEF, "M") + embed_all
    base_l = TURNS * turn_cost(BRIEF, "L") + embed_all
    print("C2 model per stage ($ / month):")
    for stage, _, _, _, cost in c2_rows:
        extra = f"  (option: re-ranker +{money(rerank)})" if stage == "Re-ranking" else ""
        print(f"  {stage:<19} {C2_SHORT[stage]:<33} {money(cost):>7}{extra}")
    print(f"  report: {ANALYSIS_DIR / 'model_choices.md'}")
    print()
    print(f"C3 cost model: {TURNS:,} turns/month, budget ${BUDGET:,}")
    print(f"  plan            {money(p['Total']):>8} / month  ({p['Total'] / BUDGET:.0%} of budget, "
          "sum of C2 stages)")
    print(f"  all Tier M      {money(base_m):>8} / month")
    print(f"  all Tier L      {money(base_l):>8} / month")
    print(f"  measured tokens {money(pm['Total']):>8} / month")
    print(f"  budget breaks if Tier M share > {break_even[TURNS]:.0%} "
          f"(> {break_even[2 * TURNS]:.0%} if usage doubles, now {m:.1%})")
    print(f"  report: {ANALYSIS_DIR / 'cost_model.md'}")


if __name__ == "__main__":
    main()
