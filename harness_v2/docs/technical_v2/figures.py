"""Draw the figures of technical document v2 (needs matplotlib).

Usage: python figures.py OUTDIR
  fig1_overview.png   the harness in three boxes, at overview level
  fig_build.png       Stage 2, from papers to codebook, in three lanes (us, model, program)
  fig_code.png        Stage 3, coding a round of interviews, in the same three lanes
The two process figures are drawn from process.json, the same file as the process page.
"""
import json
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(sys.argv[1])
FILL = {"us": "#D7EBD5", "model": "#FBE3C4", "program": "#DCE6F2"}
EDGE, INK, GREY, LOOP, CHECK = "#4A4A4A", "#1A1A1A", "#666666", "#8A3B12", "#2F6B3A"
PROCESS = json.loads((Path(__file__).with_name("process.json")).read_text(encoding="utf-8"))


def overview(path):
    fig, ax = plt.subplots(figsize=(10, 6.1))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.1); ax.axis("off")
    boxes = [
        ("1  Build the codebook", "Stages 1 and 2", [
            ("us", "Read the literature; choose\nthe works to integrate"),
            ("us", "Pose the question; split it into\nsub-questions and groups"),
            ("us", "Choose the archival data"),
            ("model", "Draft codes from the chosen\npapers, each with its evidence"),
            ("us", "Review: codes fit their quotes\nand their literature"),
        ], "frozen codebook"),
        ("2  Code the interviews", "Stage 3", [
            ("model", "Code a round of\n25 interviews"),
            ("us", "Code the same round by hand"),
            ("program", "Compare: agreement\nand anomalies"),
            ("us", "Reconcile; revise\nthe codebook"),
            ("model", "When agreement holds: code\nthe whole corpus; we spot-check"),
        ], "coded interviews"),
        ("3  Analyse", "Stage 4", [
            ("program", "Count codes and patterns"),
            ("us", "Study the anomalies: what\nthe literature does not explain"),
            ("us", "Interpret and build theory"),
        ], "findings"),
    ]
    W, X0, GAP, TOP, BOT, SH, SG = 2.95, 0.12, 0.45, 5.25, 0.55, 0.62, 0.2
    centers = {}
    for i, (title, stages, steps, out) in enumerate(boxes):
        x = X0 + i * (W + GAP)
        ax.add_patch(FancyBboxPatch((x, BOT), W, TOP - BOT, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=EDGE, lw=1.2))
        ax.text(x + 0.14, TOP - 0.24, title, fontsize=11, weight="bold", color=INK, va="center")
        ax.text(x + 0.14, TOP - 0.5, stages, fontsize=7.4, color=GREY, va="center")
        lp = 0.42 if i == 0 else 0.16
        for k, (who, text) in enumerate(steps):
            top = TOP - 0.72 - k * (SH + SG)
            ax.add_patch(FancyBboxPatch((x + lp, top - SH), W - lp - 0.16, SH, boxstyle="round,pad=0.01,rounding_size=0.06", fc=FILL[who], ec="none"))
            ax.text(x + lp + 0.14, top - SH / 2, text, fontsize=7.9, color=INK, va="center", linespacing=1.15)
            centers[(i, k)] = (x + lp, x + W - 0.16, top - SH, top)
            if k:
                xm = x + (lp + W - 0.16) / 2
                ax.add_patch(FancyArrowPatch((xm, top + SG - 0.01), (xm, top + 0.01), arrowstyle="-|>", mutation_scale=9, lw=1.0, color=EDGE))
        ax.text(x + W / 2, BOT - 0.24, f"Out: {out}", fontsize=8.8, color=INK, ha="center", va="center", weight="bold")
        if i < 2:
            ax.add_patch(FancyArrowPatch((x + W + 0.03, TOP - 0.24), (x + W + GAP - 0.03, TOP - 0.24), arrowstyle="-|>", mutation_scale=14, lw=1.5, color=EDGE))

    def side(i, k, right=True):
        l, r, b, t = centers[(i, k)]
        return (r if right else l, (b + t) / 2)
    p, q = side(0, 4, False), side(0, 3, False)
    ax.add_patch(FancyArrowPatch((p[0] - 0.02, p[1]), (q[0] - 0.02, q[1]), connectionstyle="arc3,rad=-0.9", arrowstyle="-|>", mutation_scale=9, lw=1.1, color=LOOP))
    ax.text(q[0] + 0.06, (p[1] + q[1]) / 2, "adjust, redraft", fontsize=6.4, color=LOOP, va="center")
    p, q = side(1, 3), side(1, 0)
    ax.add_patch(FancyArrowPatch((p[0] + 0.02, p[1]), (q[0] + 0.02, q[1]), connectionstyle="arc3,rad=0.55", arrowstyle="-|>", mutation_scale=9, lw=1.1, color=LOOP))
    ax.text(q[0] + 0.12, q[1] - 0.95, "next\nround", fontsize=6.6, color=LOOP, va="center")
    p, q = side(1, 3, False), side(0, 4)
    ax.add_patch(FancyArrowPatch((p[0] - 0.02, p[1]), (q[0] + 0.02, q[1]), connectionstyle="arc3,rad=0.15", arrowstyle="-|>", mutation_scale=10, lw=1.2, color=LOOP, linestyle=(0, (3, 2))))
    ax.text(X0 + W + GAP / 2, p[1] + 0.42, "revise\ncode-\nbook", fontsize=6.2, color=LOOP, ha="center", va="center")
    legend(ax, 5.55, 5.8)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")


def legend(ax, x, y):
    for kx, who in zip((x - 0.4, x + 1.0, x + 2.0), ("us", "model", "program")):
        ax.add_patch(FancyBboxPatch((kx, y - 0.08), 0.22, 0.16, boxstyle="round,pad=0.01", fc=FILL[who], ec="none"))
        ax.text(kx + 0.3, y, {"us": "researchers", "model": "model", "program": "program"}[who], fontsize=8, va="center", color=INK)


def lanes(phase, path):
    steps = phase["steps"]
    n = len(steps)
    cw, bw, bh, x0 = 1.18, 1.06, 0.9, 1.45      # column width, box width and height, first box
    rows = {"us": 2.4, "model": 1.3, "program": 0.2}
    width = x0 + 0.1 + n * cw
    fig, ax = plt.subplots(figsize=(width * 0.92, 3.6))
    ax.set_xlim(0, width); ax.set_ylim(-0.45, 3.55); ax.axis("off")
    for who, y in rows.items():
        ax.add_patch(FancyBboxPatch((0.05, y - 0.08), width - 0.1, bh + 0.16, boxstyle="round,pad=0,rounding_size=0.05",
                                    fc="#F7F7F7", ec="none"))
        ax.text(0.15, y + bh / 2, {"us": "Researchers", "model": "Model", "program": "Program"}[who],
                fontsize=8, weight="bold", color=INK, va="center")
    prev = None
    for k, s in enumerate(steps):
        x = x0 + k * cw
        y = rows[s["who"]]
        ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.01,rounding_size=0.06", fc=FILL[s["who"]],
                                    ec=CHECK if s.get("check") else "none", lw=1.6))
        ax.text(x + 0.06, y + bh - 0.1, str(k + 1), fontsize=7, weight="bold", color=GREY, va="top")
        ax.text(x + bw / 2, y + bh / 2 - 0.04, "\n".join(textwrap.wrap(s["what"], 17)), fontsize=5.4, color=INK,
                ha="center", va="center", linespacing=1.08)
        if s.get("check"):
            ax.text(x + bw - 0.06, y + bh - 0.1, "we decide", fontsize=5.2, color=CHECK, ha="right", va="top", weight="bold")
        if prev:
            px, py = prev
            ax.add_patch(FancyArrowPatch((px + bw, py + bh / 2), (x, y + bh / 2), connectionstyle="arc3,rad=0",
                                         arrowstyle="-|>", mutation_scale=8, lw=0.9, color=EDGE))
        prev = (x, y)
    x_end = x0 + n * cw
    ax.text(x_end - 0.1, -0.28, f"Out: {phase['out']}", fontsize=8, weight="bold", ha="right", color=INK)
    ax.text(x0, 3.42, phase["containers"], fontsize=7, color=GREY, ha="left", style="italic")
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    overview(OUT / "fig1_overview.png")
    for phase, name in zip(PROCESS["phases"], ("fig_build.png", "fig_code.png")):
        lanes(phase, OUT / name)
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("fig*.png"))))
