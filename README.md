# Veteran Daily-Life Assistant (RAG prototype)

Prototype for Part 2, Section B of the Military.com case study. It answers questions from veterans, service members and families using only the provided knowledge pack, and cites doc_ids.

## How it works

```
question → input guards → BM25 retrieval → router → profile + facts → generate → output checks → answer
```

- Ingestion applies rules from document metadata (trust, freshness, injection, duplicates). 19 of 24 docs are indexed. D03, D07, D11, D20 and D22 are excluded, with reasons in `outputs/ingest/manifest.csv`.
- Input guards are regexes that run before the model. PII is redacted first, so the model and the logs never see it. A crisis gets a fixed Veterans Crisis Line reply. Injection and junk are refused. Claim lookups, outcome predictions, legal and medical questions get a fixed decline with a referral. None of these call the model.
- Retrieval uses BM25, with each score multiplied by trust × freshness. The top 5 chunks go to the model.
- The router sends personalized or multi-doc questions to Tier M (Claude Sonnet 5.5) and simple FAQs to Tier S (Claude Haiku 5.5).
- Profile fields are used only if the user opted in, and only the fields the topic needs (D23). Date math is done in code: years since separation, days until separation.
- Generation returns structured output: answer, cited doc_ids, and whether the pack covers the question. Without an API key, a mock copies sentences from the retrieved docs.
- Output checks require citations to be retrieved and indexed docs, with no PII and no links outside an allowlist. A failing answer is replaced by a safe fallback.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync
cp .env.example .env    # PowerShell: Copy-Item .env.example .env
```

Put your key in `.env` (`ANTHROPIC_API_KEY=sk-ant-...`). Leave it empty to use the free mock.

## Ask your own questions

```
uv run python -m src.chat                # as a guest
uv run python -m src.chat --persona P1   # as a persona from data/personas.json
```

Each answer is followed by what happened: route, model, citations, retrieved docs, profile fields, computed facts, PII redacted, guard triggered. Questions are answered one at a time, with no memory of earlier turns.

## Run the eval

```
uv run python -m src.assistant.ingest                 # manifest + chunks (optional, for inspection)
uv run python -m src.evaluation.run_eval --repeat 3   # answers Q01-Q15, 3 runs (~$0.10 per run)
uv run python -m src.evaluation.score                 # scores every run + summary (free)
```

Claude answers vary between runs, so report the pass rate over several runs. Start with `outputs/runs/summary.md`.

The answer key is `src/evaluation/gold.yaml`. Each question checks the reply type, required citations, required and forbidden content, retrieval, PII handling and which profile fields were sent.

## Outputs

```
outputs/
  ingest/
    manifest.csv                every doc, indexed or excluded, and why
    chunks.jsonl                what gets searched
  runs/
    summary.md                  headline, pass rate per question, reasons for failures
    <timestamp>_<generator>/    one folder per run
      answers.md, answers.json  the answers and how each was produced
      scores.md, scores.json    every check, per question
      run.json                  generator, tokens, git commit, prompt and gold hashes
  logs/
    request_log.jsonl           redacted log of every request (not committed)
```

## Layout

```
data/                provided files, untouched
src/config.py        paths, as-of date (2026-10-07), .env loading
src/chat.py          interactive terminal chat
src/assistant/       the request path
  ingest.py            ingestion policy → manifest + chunks
  retrieve.py          BM25 × trust × freshness
  pii.py               redaction
  input_guards.py      crisis, injection, junk, declines
  output_checks.py     citations, PII, link allowlist
  generate.py          prompt, Claude call, mock
  pipeline.py          routing, profile, date facts, wiring, logging
src/evaluation/      gold.yaml, run_eval.py, score.py
src/analysis/        Section C scripts (traffic mix, cost model), not built yet
```

## Known limits

- Guards are regexes. They miss rephrased cases. Production would add a small classifier on top.
- BM25 matches exact words only. Some expected docs rank 3rd or 4th but are always in the top 5.
- The router's multi-doc rule fires on most questions, so most model calls go to Sonnet. It needs tuning on real traffic.
- No conversation memory. Each question is answered on its own.
- The pack's front matter is not valid YAML (unquoted colons in titles), so it is parsed line by line.
