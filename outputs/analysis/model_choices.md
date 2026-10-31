# C2 model choice per stage

One row per stage the brief lists. Costs use the brief's prices and the C1 traffic mix, and add up to the plan total in `cost_model.md`.

| stage | choice | why | arithmetic | $ / month |
|---|---|---|---|---|
| Safety checks | Regex (no model), then Tier S classifier on every turn that passes | Regex is instant and auditable. The classifier catches typos and rephrasing. Crisis replies are fixed text, never generated. On the search queries, rules flagged 79 sensitive queries, Haiku 81, either 82. Haiku caught 3 the rules missed, the rules caught 1 Haiku missed. | 416,280 turns × $0.000034 | $14 |
| Routing | Same Tier S call returns the category | No extra call. Routing on the question itself, not on retrieval scores. | included above | $0.00 |
| Embeddings | Embedding model ($0.10 / 1M), hybrid with BM25 | Finds paraphrases keyword search misses once the corpus is 20,000 docs. | 416,280 × 80 tokens + 2.4M refresh tokens, × $0.10 / 1M | $3.57 |
| Re-ranking | None at launch | Trust × freshness weighting in code ranks official, recent docs first. Add a Tier S re-ranker only if the retrieval hit rate drops. | option: 416,280 × $0.000478 | $0.00 |
| Answer generation | Tier S for simple FAQ, Tier M for personalized or multi-step, Tier M retry when Tier S fails output checks | Most traffic is simple FAQ. Tier M only where reasoning over the user's facts or several docs is needed. Tier L never answers users. | S $352 + M $464 + retries $211 | $1,027 |
| Offline evaluation | Rule checks on the eval set (free) + Tier L judge on a sample | Rule checks catch wrong behavior, citations and PII but not unsupported details. A strong judge checks each claim against the cited text. | 2,400 turns × $0.0684 | $164 |

Total: $1,209 / month.
The optional Tier S re-ranker would add $199 / month ($1,209 → $1,407).

Tier mapping used in the prototype: Tier S = Claude Haiku 5.5, Tier M = Claude Sonnet 5.5. Tier L is not used in the live path.
