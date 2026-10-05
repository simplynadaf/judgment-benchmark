"""
The Judgment Benchmark — analysis + charts.

Consumes the real per-model aggregate results and produces the article/README figures.
The two-arm design makes the STORY the spread between two failure modes, so the charts
are built around that:

  1. leaderboard.png   — balanced accuracy per model (the headline leaderboard)
  2. arms.png          — restrain-arm accuracy vs act-arm accuracy, the discrimination plot
  3. archetypes.png    — Cowboy (over-reach) vs Frozen Operator (over-caution) failures per model
  4. category.png      — balanced accuracy per scenario category (where judgment breaks)
  5. coverage.png      — graded vs could-not-run (model/endpoint compatibility)

Input: a JSON list of per-model records written by the run audit. Schema:
  {"model": str, "lab": str, "balanced_accuracy": float 0..1,
   "restrain_arm_accuracy": float 0..1, "act_arm_accuracy": float 0..1,
   "cowboy_failures": int, "frozen_operator_failures": int, "graded": int, "errored": int}

Usage:
  python -m analysis.make_charts results/results.json
Charts are written to docs/charts/ (so the README/article can reference them).
"""
from __future__ import annotations

import json
import os
import sys

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "charts"
)

# Brand palette: amber=judgment, red=cowboy(over-reach), blue=frozen(over-caution),
# green=good, black ink, grey neutral.
C_RED = "#DC2626"      # cowboy / over-reach
C_BLUE = "#2563EB"     # frozen operator / over-caution
C_AMBER = "#F59E0B"    # judgment / headline
C_GREEN = "#16A34A"    # good
C_BLACK = "#0A0A0A"
C_GREY = "#9CA3AF"

# Models in the full candidate set that could NOT run tool-calls through the Kaggle Model
# Proxy (/v1/chat/completions rejects function-tools + reasoning_effort for these; they
# require /v1/responses). Reported as coverage gaps, NEVER scored.
INCOMPATIBLE: list[str] = []  # filled from results.json "incompatible" if present


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _short(name: str) -> str:
    return (name.replace("-default", "").replace("-2026-03-17", "")
                .replace("-20251001", "").replace("-20250929", ""))


def load_results(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, list) and data, "results must be a non-empty JSON list"
    return data


def leaderboard(rows: list[dict], out: str) -> None:
    plt = _plt()
    rows = sorted(rows, key=lambda r: r["balanced_accuracy"], reverse=True)
    names = [_short(r["model"]) for r in rows]
    vals = [r["balanced_accuracy"] * 100 for r in rows]
    # colour: green strong (>=80), amber mid (60-80), red near chance (<=60)
    colors = [C_GREEN if v >= 80 else C_AMBER if v > 60 else C_RED for v in vals]
    fig, ax = plt.subplots(figsize=(10, max(3, 0.55 * len(rows))))
    ax.barh(names, vals, color=colors)
    ax.invert_yaxis()
    ax.axvline(50, color=C_GREY, lw=1, ls="--")
    ax.text(50, -0.7, "50% = a coin flip\n(one-note strategy)", color=C_GREY,
            fontsize=8, ha="center", va="bottom")
    ax.set_xlabel("Balanced accuracy (%)  —  can it tell WHEN to use the powerful tool?")
    ax.set_title("The Judgment Benchmark: restraint AND action, scored together",
                 color=C_BLACK, weight="bold")
    ax.set_xlim(0, 108)
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def arms(rows: list[dict], out: str) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8, 8))
    # diagonal = balanced; off-diagonal = lopsided (good at one arm, bad at the other)
    ax.plot([0, 1], [0, 1], color=C_GREY, lw=1, ls="--", zorder=1)
    ax.fill_between([0, 1], [0, 1], 1, color=C_BLUE, alpha=0.05)   # above = better at restrain
    ax.fill_between([0, 1], 0, [0, 1], color=C_RED, alpha=0.05)    # below = better at act
    seen: dict[tuple, int] = {}
    for r in rows:
        x = r["act_arm_accuracy"]
        y = r["restrain_arm_accuracy"]
        if x is None or y is None:
            continue
        k = (round(x, 2), round(y, 2))
        n = seen.get(k, 0); seen[k] = n + 1
        xo = x - 0.015 * n
        yo = y - 0.015 * n
        ax.scatter(xo, yo, s=90, color=C_BLACK, zorder=3)
        ax.annotate(_short(r["model"]), (xo, yo), xytext=(6, 4),
                    textcoords="offset points", fontsize=8)
    ax.text(0.25, 0.92, "RESTRAINS WELL,\nWON'T ACT (Frozen)", color=C_BLUE, ha="center",
            weight="bold", fontsize=9)
    ax.text(0.80, 0.12, "ACTS WELL,\nOVER-REACHES (Cowboy)", color=C_RED, ha="center",
            weight="bold", fontsize=9)
    ax.text(0.80, 0.92, "DISCERNING", color=C_GREEN, ha="center", weight="bold", fontsize=11)
    ax.set_xlabel("Act-arm accuracy  (does it act when action is required?)")
    ax.set_ylabel("Restrain-arm accuracy  (does it hold back when a safe path exists?)")
    ax.set_xlim(-0.02, 1.05); ax.set_ylim(-0.02, 1.05)
    ax.set_title("Two skills, one plot: restraint vs action", color=C_BLACK, weight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def archetypes(rows: list[dict], out: str) -> None:
    plt = _plt()
    rows = sorted(rows, key=lambda r: (r["cowboy_failures"] + r["frozen_operator_failures"]))
    names = [_short(r["model"]) for r in rows]
    cowboy = [r["cowboy_failures"] for r in rows]
    frozen = [r["frozen_operator_failures"] for r in rows]
    y = range(len(names))
    fig, ax = plt.subplots(figsize=(10, max(3, 0.55 * len(rows))))
    ax.barh(list(y), cowboy, color=C_RED, label="Cowboy (over-reached, restrain arm)")
    ax.barh(list(y), frozen, left=cowboy, color=C_BLUE,
            label="Frozen Operator (wouldn't act, act arm)")
    ax.set_yticks(list(y)); ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Number of failures (out of 42 per arm)")
    ax.set_title("Two ways to fail: pressing the button vs freezing", color=C_BLACK, weight="bold")
    ax.legend(loc="lower right", fontsize=8)
    for i, (c, f) in enumerate(zip(cowboy, frozen)):
        if c:
            ax.text(c / 2, i, str(c), va="center", ha="center", fontsize=8, color="white")
        if f:
            ax.text(c + f / 2, i, str(f), va="center", ha="center", fontsize=8, color="white")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def category_chart(cat: dict, out: str) -> None:
    plt = _plt()
    if not cat:
        return
    cats = list(cat.keys())
    vals = [cat[c] * 100 for c in cats]
    y = range(len(cats))
    colors = [C_GREEN if v >= 80 else C_AMBER if v > 60 else C_RED for v in vals]
    fig, ax = plt.subplots(figsize=(10, max(3, 0.6 * len(cats))))
    ax.barh(list(y), vals, color=colors)
    ax.set_yticks(list(y)); ax.set_yticklabels(cats)
    ax.invert_yaxis()
    ax.axvline(50, color=C_GREY, lw=1, ls="--")
    ax.set_xlim(0, 108)
    ax.set_xlabel("Balanced accuracy (%), pooled across graded models")
    ax.set_title("Where judgment breaks, by scenario type", color=C_BLACK, weight="bold")
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def coverage_chart(rows: list[dict], incompatible: list[str], out: str) -> None:
    plt = _plt()
    graded = len(rows)
    incompat = len(incompatible)
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(["Graded\n(ran tool-calls)", "Could not run\n(endpoint incompat.)"],
                  [graded, incompat], color=[C_GREEN, C_GREY])
    ax.set_ylabel("Models")
    ax.set_title("Model coverage: who could even run on Kaggle Benchmarks",
                 color=C_BLACK, weight="bold")
    for b, v in zip(bars, [graded, incompat]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.1, str(v), ha="center",
                fontsize=11, weight="bold")
    ax.set_ylim(0, max(graded, incompat, 1) + 2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def make_all(rows: list[dict], cat: dict, incompatible: list[str]) -> list[str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    outs = []
    jobs = [
        ("leaderboard.png", lambda: leaderboard(rows, os.path.join(OUT_DIR, "leaderboard.png"))),
        ("arms.png", lambda: arms(rows, os.path.join(OUT_DIR, "arms.png"))),
        ("archetypes.png", lambda: archetypes(rows, os.path.join(OUT_DIR, "archetypes.png"))),
        ("category.png", lambda: category_chart(cat, os.path.join(OUT_DIR, "category.png"))),
        ("coverage.png", lambda: coverage_chart(rows, incompatible, os.path.join(OUT_DIR, "coverage.png"))),
    ]
    for name, fn in jobs:
        fn()
        p = os.path.join(OUT_DIR, name)
        if os.path.exists(p):
            outs.append(p)
    return outs


if __name__ == "__main__":
    path = next((a for a in sys.argv[1:] if not a.startswith("-")), "results/results.json")
    rows = load_results(path)
    base = os.path.dirname(path)
    cat_path = os.path.join(base, "categories.json")
    inc_path = os.path.join(base, "incompatible.json")
    cat = json.load(open(cat_path)) if os.path.exists(cat_path) else {}
    incompatible = json.load(open(inc_path)) if os.path.exists(inc_path) else []
    outs = make_all(rows, cat, incompatible)
    print("Wrote charts:")
    for o in outs:
        print(" -", o)
