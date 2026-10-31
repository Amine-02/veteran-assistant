# C1 traffic mix (search_queries.csv)

4,000 queries, 1,987 sessions, 1,239 unique texts after redaction. Labels come from rules that reuse the assistant's input guards (see `src/analysis/traffic_mix.py`).

## Shares

| category | queries | share of queries | sessions with 1+ | share of sessions | route |
|---|---|---|---|---|---|
| simple_faq | 3,125 | 78.1% | 1,717 | 86.4% | S |
| personalized | 344 | 8.6% | 315 | 15.9% | M |
| sensitive | 79 | 2.0% | 63 | 3.2% | none |
| out_of_scope | 251 | 6.3% | 201 | 10.1% | none |
| junk | 201 | 5.0% | 126 | 6.3% | none |

## Breakdown of sensitive, out of scope and junk

| category | reason | queries | share |
|---|---|---|---|
| out_of_scope | outcome_prediction | 107 | 2.7% |
| junk | injection | 101 | 2.5% |
| out_of_scope | account | 100 | 2.5% |
| junk | junk | 100 | 2.5% |
| sensitive | pii | 46 | 1.1% |
| out_of_scope | legal | 44 | 1.1% |
| sensitive | crisis | 33 | 0.8% |

## Topics of in-scope questions (simple FAQ + personalized)

The 24-doc pilot pack covers about 79.9% of in-scope questions by topic. The rest get a "not covered" reply until the sources in A2 are added.

| topic | queries | covered by pack |
|---|---|---|
| gi_bill | 719 | yes |
| discounts | 475 | yes |
| jobs | 431 | yes |
| claims_disability | 373 | yes |
| health_care | 302 | yes |
| home_loan | 285 | yes |
| state_benefits | 210 | no |
| transition | 188 | yes |
| other | 128 | no |
| tricare_insurance | 104 | no |
| pay_retirement | 95 | no |
| survivor_burial | 83 | no |
| id_travel | 76 | no |

## Second opinion: Claude Haiku labels

Haiku labeled 1,239 unique texts independently. Agreement with the rules: 97.2% of queries.

| category | rules | Haiku |
|---|---|---|
| simple_faq | 78.1% | 76.5% |
| personalized | 8.6% | 8.2% |
| sensitive | 2.0% | 2.0% |
| out_of_scope | 6.3% | 8.1% |
| junk | 5.0% | 5.1% |

### Where they disagree

| rules say | Haiku says | queries | examples |
|---|---|---|---|
| personalized | out_of_scope | 47 | increase my va rating from 70%; increase my va rating from 40%; increase my va rating from 100% |
| simple_faq | personalized | 33 | hey free help filing va claim vso near me; am ie ligible for va health care; pls effective date va disability back pay |
| simple_faq | out_of_scope | 25 | hey ebenefits login not working; question: ebenefits login not working; do i need al awyer for va claim |
| simple_faq | junk | 4 | cancel newsletetr; cancel enwsletter?; cancel newseltter? |
| simple_faq | sensitive | 2 | how do i get help i'm noto k?; i want toe nd it all |
| personalized | sensitive | 1 | i dont see the pointa nymore since i got out? |
| sensitive | simple_faq | 1 | quick q veterans crisis line number |

## Hand check

Reference labels (`your_category`) on 100 sampled queries. Agreement: rules 99/100, Haiku 97/100.
- how long do i have to use my gi bill: rules simple_faq, reference personalized

Files: `traffic_mix.csv` (every query, redacted, with labels), `hand_check_sample.csv` (100 unique queries to label by hand), `traffic_mix.json` (shares used by cost_model.py).
