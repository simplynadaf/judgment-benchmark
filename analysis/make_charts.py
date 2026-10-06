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

    # Base: SciencePlots for publication-grade typography, spines and grid. 'no-latex'
    # because we run headless (no TeX). 'grid' adds a light reference grid. We then layer
    # our brand palette + highlights on top of this clean foundation.
    try:
        import scienceplots  # noqa: F401 (registers the styles)
        plt.style.use(["science", "no-latex", "grid"])
    except Exception:
        plt.style.use("seaborn-v0_8-whitegrid")

    # House overrides so every figure is consistent, legible, and on-brand.
    plt.rcParams.update({
        "figure.dpi": 220,              # crisp PNG for retina / README zoom
        "savefig.dpi": 220,
        "savefig.bbox": "tight",
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlepad": 14,
        "axes.labelsize": 11,
        "axes.labelcolor": "#1F2937",
        "axes.edgecolor": "#D1D5DB",
        "axes.linewidth": 0.9,
        "axes.grid.axis": "x",
        "grid.color": "#E5E7EB",
        "grid.linewidth": 0.8,
        "xtick.color": "#6B7280",
        "ytick.color": "#1F2937",
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "legend.edgecolor": "#E5E7EB",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })
    return plt


def _style_axes(ax, grid_axis="x"):
    """Strip chart junk: no top/right spines, grid on one axis only, soft ticks."""
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#D1D5DB")
    ax.tick_params(length=0)
    ax.set_axisbelow(True)
    if grid_axis == "x":
        ax.grid(axis="x", color="#E5E7EB", lw=0.8)
        ax.grid(axis="y", visible=False)
    elif grid_axis == "y":
        ax.grid(axis="y", color="#E5E7EB", lw=0.8)
        ax.grid(axis="x", visible=False)
    else:
        ax.grid(axis="both", color="#EEF0F2", lw=0.7)


def _plt_legacy():
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
    worst = min(vals)
    # Hero highlight: the clear outlier (worst) in amber, the rest in a calm green.
    colors = [C_AMBER if v == worst else C_GREEN for v in vals]
    fig, ax = plt.subplots(figsize=(10, max(3.2, 0.6 * len(rows))))
    bars = ax.barh(names, vals, color=colors, edgecolor="white", linewidth=0.8, height=0.72)
    ax.invert_yaxis()
    ax.axvline(50, color=C_GREY, lw=1.1, ls=(0, (4, 3)))
    ax.text(50, len(rows) - 0.3, "50% = coin flip\n(one-note strategy)", color=C_GREY,
            fontsize=8.5, ha="center", va="top")
    ax.set_xlabel("Balanced accuracy (%) — can it tell WHEN to use the powerful tool?")
    ax.set_title("The Judgment Benchmark: restraint AND action, scored together")
    ax.set_xlim(0, 112)
    for i, v in enumerate(vals):
        inside = v > 15
        ax.text(v - 2 if inside else v + 1.5, i, f"{v:.1f}%", va="center",
                ha="right" if inside else "left", fontsize=9.5, weight="bold",
                color="white" if inside else C_BLACK)
    _style_axes(ax, "x")
    fig.text(0.01, 0.01, "Higher = better judgment. 1.0 only if it both restrains and acts correctly.",
             fontsize=7.5, color=C_GREY)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def arms(rows: list[dict], out: str) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.5, 8))
    # Quadrant shading: above diagonal = better at restraint, below = better at action.
    ax.plot([0, 1], [0, 1], color=C_GREY, lw=1.1, ls=(0, (4, 3)), zorder=1)
    ax.fill_between([0, 1], [0, 1], 1, color=C_BLUE, alpha=0.045, zorder=0)
    ax.fill_between([0, 1], 0, [0, 1], color=C_RED, alpha=0.045, zorder=0)

    pts = [(r["act_arm_accuracy"], r["restrain_arm_accuracy"], r)
           for r in rows if r["act_arm_accuracy"] is not None and r["restrain_arm_accuracy"] is not None]

    texts = []
    for x, y, r in pts:
        # Hero: the lopsided outlier (low act, high restrain) = the Frozen Operator story.
        is_frozen = (y - x) > 0.25
        color = C_AMBER if is_frozen else C_GREEN
        size = 150 if is_frozen else 70
        ax.scatter(x, y, s=size, color=color, edgecolor=C_BLACK, linewidth=1.1,
                   zorder=4, alpha=0.95)
        label = _short(r["model"])
        texts.append(ax.text(x, y, label, fontsize=8.5,
                             weight="bold" if is_frozen else "normal",
                             color=C_BLACK, zorder=5))

    try:
        from adjustText import adjust_text
        adjust_text(texts, ax=ax,
                    expand=(1.3, 1.6),
                    arrowprops=dict(arrowstyle="-", color="#9CA3AF", lw=0.7),
                    only_move={"text": "xy", "static": "xy"})
    except Exception:
        pass

    ax.text(0.24, 0.95, "RESTRAINS WELL,\nWON'T ACT  (Frozen Operator)", color=C_BLUE,
            ha="center", weight="bold", fontsize=9.5)
    ax.text(0.80, 0.08, "ACTS WELL,\nOVER-REACHES  (Cowboy)", color=C_RED, ha="center",
            weight="bold", fontsize=9.5)
    ax.text(0.86, 0.96, "DISCERNING", color=C_GREEN, ha="center", weight="bold", fontsize=12)
    # Call out that the Cowboy quadrant is EMPTY — a finding in itself.
    ax.text(0.80, 0.015, "(nobody landed here)", color=C_RED, ha="center",
            fontsize=8, style="italic", alpha=0.8)

    ax.set_xlabel("Act-arm accuracy  →  does it act when action is required?")
    ax.set_ylabel("Restrain-arm accuracy  →  does it hold back when a safe path exists?")
    ax.set_xlim(-0.03, 1.06); ax.set_ylim(-0.03, 1.08)
    ax.set_title("Two skills, one plot: restraint vs action")
    _style_axes(ax, "both")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def archetypes(rows: list[dict], out: str) -> None:
    plt = _plt()
    rows = sorted(rows, key=lambda r: (r["cowboy_failures"] + r["frozen_operator_failures"]))
    names = [_short(r["model"]) for r in rows]
    cowboy = [r["cowboy_failures"] for r in rows]
    frozen = [r["frozen_operator_failures"] for r in rows]
    y = range(len(names))
    total_cowboy = sum(cowboy)
    fig, ax = plt.subplots(figsize=(10, max(3.2, 0.6 * len(rows))))
    ax.barh(list(y), cowboy, color=C_RED, label="Cowboy — over-reached (restrain arm)",
            edgecolor="white", linewidth=0.8, height=0.72)
    ax.barh(list(y), frozen, left=cowboy, color=C_BLUE,
            label="Frozen Operator — wouldn't act (act arm)",
            edgecolor="white", linewidth=0.8, height=0.72)
    ax.set_yticks(list(y)); ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Number of failures (out of 42 per arm)")
    ax.set_title("Two ways to fail: pressing the button vs freezing")
    ax.legend(loc="lower right", fontsize=8.5, borderpad=0.7)
    maxv = max([c + f for c, f in zip(cowboy, frozen)] + [1])
    ax.set_xlim(0, maxv * 1.12)
    for i, (c, f) in enumerate(zip(cowboy, frozen)):
        if c:
            ax.text(c / 2, i, str(c), va="center", ha="center", fontsize=8.5,
                    color="white", weight="bold")
        if f:
            ax.text(c + f / 2, i, str(f), va="center", ha="center", fontsize=8.5,
                    color="white", weight="bold")
    _style_axes(ax, "x")
    # Surface the headline finding: no model over-reached at all.
    if total_cowboy == 0:
        fig.text(0.01, 0.01,
                 "Not one Cowboy failure in the whole lineup — in 2026 the failure mode is "
                 "over-caution, not recklessness.",
                 fontsize=8, color=C_RED, style="italic")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def category_chart(cat: dict, out: str) -> None:
    plt = _plt()
    if not cat:
        return
    # Sort hardest-first so the eye lands on where judgment breaks.
    items = sorted(cat.items(), key=lambda kv: kv[1])
    cats = [k for k, _ in items]
    vals = [v * 100 for _, v in items]
    y = range(len(cats))
    worst = min(vals)
    colors = [C_AMBER if v == worst else C_GREEN for v in vals]
    fig, ax = plt.subplots(figsize=(10, max(3.2, 0.6 * len(cats))))
    ax.barh(list(y), vals, color=colors, edgecolor="white", linewidth=0.8, height=0.72)
    ax.set_yticks(list(y)); ax.set_yticklabels([c.replace("_", " ") for c in cats])
    ax.invert_yaxis()
    ax.axvline(50, color=C_GREY, lw=1.1, ls=(0, (4, 3)))
    ax.set_xlim(0, 112)
    ax.set_xlabel("Balanced accuracy (%), pooled across graded models")
    ax.set_title("Where judgment breaks, by scenario type")
    for i, v in enumerate(vals):
        ax.text(v - 2, i, f"{v:.0f}%", va="center", ha="right", fontsize=9,
                color="white", weight="bold")
    _style_axes(ax, "x")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def coverage_chart(rows: list[dict], incompatible: list[str], out: str) -> None:
    plt = _plt()
    graded = len(rows)
    incompat = len(incompatible)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bars = ax.bar(["Graded\n(ran tool-calls)", "Could not run\n(endpoint incompatible)"],
                  [graded, incompat], color=[C_GREEN, C_GREY], width=0.6,
                  edgecolor="white", linewidth=1)
    ax.set_ylabel("Models")
    ax.set_title("Model coverage: who could even run on Kaggle Benchmarks")
    for b, v in zip(bars, [graded, incompat]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v), ha="center",
                fontsize=13, weight="bold", color=C_BLACK)
    ax.set_ylim(0, max(graded, incompat, 1) + 2)
    _style_axes(ax, "y")
    if incompatible:
        fig.text(0.01, 0.01, "Could not run: " + ", ".join(_short(m) for m in incompatible)
                 + "  (reported as gaps, never scored 0).",
                 fontsize=7.5, color=C_GREY)
    fig.tight_layout()
    fig.savefig(out)
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
