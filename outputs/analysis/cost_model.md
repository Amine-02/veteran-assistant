# C3 cost model

Turns per month: 40,000 × 3 × 4 = 480,000. Budget: $3,500 for model + embeddings.
Prices and token profile are the brief's assumptions.

## Cost of one turn (brief profile)

Input = 900 cached system prompt + 600 history + 1,750 retrieved + 60 user. Output 250.

- Tier S: (900 × $0.025 + 2,410 × $0.25 + 250 × $1.25) / 1M = $0.000937
- Tier M: (900 × $0.300 + 2,410 × $3.00 + 250 × $15.00) / 1M = $0.011250
- Tier L: (900 × $1.500 + 2,410 × $15.00 + 250 × $75.00) / 1M = $0.056250
- Classifier call (Tier S): (250 × $0.025 + 60 × $0.25 + 10 × $1.25) / 1M = $0.000034

## Traffic mix used (from C1)

- Tier S (simple FAQ): 78.1%
- Tier M (personalized / multi-step): 8.6%
- No model call (crisis, PII lookups, out of scope, junk): 13.3%

## Baselines

| baseline | per turn | model | embeddings | total / month | fits? |
|---|---|---|---|---|---|
| everything on Tier M | $0.01125 | $5,400 | $4.08 | **$5,404** | no |
| everything on Tier L | $0.05625 | $27,000 | $4.08 | **$27,004** | no |

## Plan (brief token profile)

| line | arithmetic | $ / month |
|---|---|---|
| Tier S answers (simple FAQ) | 480,000 × 78.1% × $0.000937 | $352 |
| Tier M answers (personalized / multi-step) | 480,000 × 8.6% × $0.01125 | $464 |
| Tier M retries (5% of Tier S answers) | 480,000 × 78.1% × 5% × $0.01125 | $211 |
| Tier S safety + routing classifier | 480,000 × 86.7% × $0.000034 | $14 |
| Query embeddings | 480,000 × 86.7% × 80 tokens × $0.10 / 1M | $3.33 |
| Corpus refresh embeddings (10%/month) | 24M tokens × 10% × $0.10 / 1M | $0.24 |
| Offline eval, Tier L judge on 0.5% of turns | 480,000 × 0.5% × $0.0684 | $164 |
| **Total** | | **$1,209** |

One-time: embedding the full corpus = 24M × $0.10 / 1M = $2.40.
The plan uses 35% of the budget, 22% of the all-Tier-M baseline.

The tier chosen for each stage, and why, is in `model_choices.md` (C2).

## What could break the budget

Search queries are short, single questions with no persona. Chat turns 2-4 are follow-ups that are more often personalized, so the Tier M share is probably higher in chat. The table moves traffic from Tier S to Tier M.

| Tier M share | 480k turns | 960k turns (usage doubles) |
|---|---|---|
| 8.6% (measured) | $1,209 | $2,417 |
| 20% | $1,742 | $3,484 |
| 30% | $2,210 | $4,420 |
| 50% | $3,146 | $6,292 |

At 480,000 turns the plan stays under $3,500 while the Tier M share is below 58%.

At 960,000 turns the plan stays under $3,500 while the Tier M share is below 20%.

## Same plan with the measured token profile

The prototype measured ~850 cached + ~1,150 other input and ~180 output per call (short pack chunks, no history). Adding 600 history tokens:

- Tier S turn: (850 × $0.025 + 1,750 × $0.25 + 180 × $1.25) / 1M = $0.000684
- Tier M turn: (850 × $0.300 + 1,750 × $3.00 + 180 × $15.00) / 1M = $0.008205
- Plan total: **$931** / month (vs $1,209 with the brief profile). Real articles are longer than the pack excerpts, so the brief profile is the safer number.

## Answer cache potential

Simple FAQ traffic has 185 distinct questions once prefixes and typos are merged. The 100 most common cover 93% of simple-FAQ queries. A cache of reviewed answers for these (invalidated on each index version) would cut most Tier S calls. Search-box text repeats more than chat does, so treat this as an upper bound.
