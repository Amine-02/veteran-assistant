"""Run the whole analysis: traffic mix (C1), then cost model (C3).

    uv run python -m src.analysis            # Haiku second opinion if a key is set
    uv run python -m src.analysis --no-llm   # rules only, free

Haiku labels are cached in outputs/analysis/llm_labels.json, so only the
first run with a key costs anything (~$0.05).
"""

from __future__ import annotations

import argparse
import os

import src.config  # noqa: F401  (loads .env)
from src.analysis import cost_model, traffic_mix


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-llm", action="store_true", help="skip the Haiku second opinion")
    args = parser.parse_args()

    use_llm = not args.no_llm and bool(os.environ.get("ANTHROPIC_API_KEY"))
    traffic_mix.main(["--llm"] if use_llm else [])
    print()
    cost_model.main()


if __name__ == "__main__":
    main()
