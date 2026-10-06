"""
Extract the chart-ready results JSONs from downloaded Kaggle run verdicts.

Reads every judgment_verdicts.json under a downloaded results dir
(e.g. ./results_final/judgment/<version>/<model>/<run>/judgment_verdicts.json),
recomputes balanced accuracy + arm accuracies + archetype counts PER MODEL from the
per-scenario verdicts (so the numbers are auditable, not taken from a single aggregate),
and writes:

  results/results.json      - list of per-model records (schema in make_charts.py)
  results/categories.json   - {category: balanced_accuracy across all models}
  results/incompatible.json - list of model slugs that could not run (reported, not scored)

Usage:
  python analysis/extract_results.py ./results_final [--incompatible slugA slugB ...]
"""
from __future__ import annotations

import glob
import json
import os
import sys

# Lab attribution for the chart labels (purely cosmetic grouping).
_LAB = {
    "claude": "Anthropic",
    "gemini": "Google",
    "gemma": "Google",
    "gpt": "OpenAI",
    "grok": "xAI",
    "qwen": "Alibaba",
    "deepseek": "DeepSeek",
    "glm": "Zhipu",
}


def _lab_of(model: str) -> str:
    for k, v in _LAB.items():
        if model.startswith(k):
            return v
    return "Other"


def _balanced(graded: list[dict]) -> tuple[float | None, float | None, float | None]:
    restrain = [v for v in graded if v.get("arm", "restrain") == "restrain"]
    act = [v for v in graded if v.get("arm") == "act"]
    ra = (sum(v["solved"] for v in restrain) / len(restrain)) if restrain else None
    aa = (sum(v["solved"] for v in act) / len(act)) if act else None
    bal = (0.5 * (ra + aa)) if (ra is not None and aa is not None) else None
    return bal, ra, aa


def extract(download_dir: str, incompatible: list[str]) -> None:
    verdict_files = sorted(glob.glob(os.path.join(download_dir, "**", "judgment_verdicts.json"), recursive=True))
    if not verdict_files:
        sys.exit(f"No judgment_verdicts.json found under {download_dir}")

    rows: list[dict] = []
    # category -> [solved flags] across all models (balanced-ish: raw solved rate per category)
    cat_solved: dict[str, list[int]] = {}

    seen_models: set[str] = set()
    for vf in verdict_files:
        # the model dir is .../<model>/<run>/judgment_verdicts.json
        model = os.path.basename(os.path.dirname(os.path.dirname(vf)))
        if model in seen_models:
            continue  # first run only (run 1); stability repeats handled separately
        seen_models.add(model)

        verdicts = json.load(open(vf))
        graded = [v for v in verdicts if not v.get("errored", False)]
        errored = len(verdicts) - len(graded)

        # A model that produced ZERO graded scenarios did not actually run (e.g. the proxy
        # rejected tool-calls for it). It is a COVERAGE GAP, never a 0.0 on the leaderboard.
        # Scoring a non-run as 0 was the exact integrity bug this benchmark is built to avoid.
        if not graded:
            if model not in incompatible:
                incompatible.append(model)
            continue

        bal, ra, aa = _balanced(graded)

        cowboy = sum(1 for v in graded if v.get("quadrant") == "cowboy")
        frozen = sum(1 for v in graded if v.get("quadrant") == "frozen_operator")

        rows.append({
            "model": model,
            "lab": _lab_of(model),
            "balanced_accuracy": round(bal, 4) if bal is not None else 0.0,
            "restrain_arm_accuracy": round(ra, 4) if ra is not None else 0.0,
            "act_arm_accuracy": round(aa, 4) if aa is not None else 0.0,
            "cowboy_failures": cowboy,
            "frozen_operator_failures": frozen,
            "graded": len(graded),
            "errored": errored,
        })

        for v in graded:
            cat_solved.setdefault(v["category"], []).append(1 if v["solved"] else 0)

    rows.sort(key=lambda r: r["balanced_accuracy"], reverse=True)

    categories = {c: round(sum(s) / len(s), 4) for c, s in sorted(cat_solved.items())}

    os.makedirs("results", exist_ok=True)
    json.dump(rows, open("results/results.json", "w"), indent=2)
    json.dump(categories, open("results/categories.json", "w"), indent=2)
    json.dump(incompatible, open("results/incompatible.json", "w"), indent=2)

    print(f"Wrote results/results.json ({len(rows)} models)")
    print(f"Wrote results/categories.json ({len(categories)} categories)")
    print(f"Wrote results/incompatible.json ({len(incompatible)} models)")
    print()
    print(f"{'model':32} {'bal':>6} {'restr':>6} {'act':>6} {'cowboy':>7} {'frozen':>7}")
    for r in rows:
        print(f"{r['model']:32} {r['balanced_accuracy']:>6.3f} {r['restrain_arm_accuracy']:>6.3f} "
              f"{r['act_arm_accuracy']:>6.3f} {r['cowboy_failures']:>7} {r['frozen_operator_failures']:>7}")


if __name__ == "__main__":
    args = sys.argv[1:]
    dl = next((a for a in args if not a.startswith("--")), "./results_final")
    incompatible: list[str] = []
    if "--incompatible" in args:
        incompatible = args[args.index("--incompatible") + 1:]
    extract(dl, incompatible)
