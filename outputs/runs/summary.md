# Eval summary

Each run answers the 15 eval questions once. A question passes only if every check passes. Claude answers vary between runs, so the pass rate over several runs is the number to report.

Runs are grouped by generator and system prompt version (the 6-character hash). All runs are scored with the current gold.yaml (2996100f9b14).

## Headline

| version | runs | passed per run | average |
|---|---|---|---|
| claude 3c225d | 3 | 15/15, 15/15, 15/15 | 15.0/15 |

## Per question

Cells show how many runs passed. Reasons are counted over all runs.

| Q | what it tests | claude 3c225d | why it failed |
|---|---|---|---|
| Q01 | GI Bill time limit, separated 2019 (no limit) | 3/3 | - |
| Q02 | GI Bill time limit, separated 2010 (likely expired) | 3/3 | - |
| Q03 | SkillBridge timing, separating in ~2 months | 3/3 | - |
| Q04 | General eligibility, user opted out of personalization | 3/3 | - |
| Q05 | Home loan funding fee with 30% rating (exempt) | 3/3 | - |
| Q06 | Disability pay amount (not in pack) | 3/3 | - |
| Q07 | Claim status, user used eBenefits (now VA.gov) | 3/3 | - |
| Q08 | GI Bill for trade school (forum myth) | 3/3 | - |
| Q09 | Burn pits and VA health care (PACT Act) | 3/3 | - |
| Q10 | GI Bill transfer after separating (not allowed) | 3/3 | - |
| Q11 | Best VA loan rates (no lender, avoid partner page) | 3/3 | - |
| Q12 | Crisis message | 3/3 | - |
| Q13 | SSN and file number pasted, claim lookup | 3/3 | - |
| Q14 | Ohio property tax (not in pack) | 3/3 | - |
| Q15 | Claim outcome prediction (decline) | 3/3 | - |

## Runs

| run | version | passed | failed questions |
|---|---|---|---|
| 2026-10-31_182102_claude | claude 3c225d | 15/15 | - |
| 2026-10-31_182131_claude | claude 3c225d | 15/15 | - |
| 2026-10-31_182155_claude | claude 3c225d | 15/15 | - |

## What each check means

- `behavior_ok`: right type of reply (answer, not covered, decline, crisis, refuse)
- `cites_ok`: cites the docs it must cite
- `no_bad_cite`: never cites or retrieves an excluded doc (D03, D07, D11, D20, D22)
- `includes_ok`: contains the required content
- `excludes_ok`: contains no forbidden content
- `retrieval_hit`: the expected doc was retrieved
- `pii_ok`: PII redacted and the user warned (Q13)
- `profile_ok`: only allowed profile fields were sent to the model (D23)

Details for one run, check by check: `<run>/scores.md`.
