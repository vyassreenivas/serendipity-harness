"""Draw the harness for page 1 of the technical document: three boxes, each a
sequence of steps, coloured by who does them, with the loops between people and model.

Usage: python flow.py flow.png   (needs matplotlib)
Box 1 builds the codebook, box 2 codes the interviews, box 3 analyses the coded
interviews. Inside box 1 the model drafts and we review until the codebook
freezes; inside box 2 we compare our coding with the model's batch by batch,
and changes go back to the codebook review.
Colours: green for us (researchers), orange for the model, blue for fixed code.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = sys.argv[1]
FILL = {"R": "#D7EBD5", "M": "#FBE3C4", "F": "#DCE6F2"}
EDGE, INK, GREY, LOOP = "#4A4A4A", "#1A1A1A", "#666666", "#8A3B12"

fig, ax = plt.subplots(figsize=(10, 6.1))
ax.set_xlim(0, 10); ax.set_ylim(0, 6.1); ax.axis("off")

BOXES = [
    ("1  Build the codebook", "Stages 1 to 5", [
        ("R", "Read the literature; choose\nthe works to integrate"),
        ("R", "Pose the question; split it into\nsub-questions and groups"),
        ("R", "Choose the archival data"),
        ("M", "Draft codes from the chosen\npapers, each with its evidence"),
        ("R", "Review: codes fit their quotes\nand their literature"),
    ], "frozen codebook"),
    ("2  Code the interviews", "Stages 6 to 8", [
        ("M", "Code a batch of\n25 to 50 interviews"),
        ("R", "Code the same batch by hand"),
        ("F", "Compare: agreement\nand anomalies"),
        ("R", "Reconcile; revise\nthe codebook"),
        ("M", "When agreement holds: code\nthe whole corpus; we spot-check"),
    ], "coded interviews"),
    ("3  Analyse", "", [
        ("F", "Count codes and patterns"),
        ("R", "Study the anomalies: what\nthe literature does not explain"),
        ("R", "Interpret and build theory"),
    ], "findings"),
]
W, X0, GAP, TOP, BOT = 2.95, 0.12, 0.45, 5.25, 0.55
SH, SG = 0.62, 0.2          # step height, gap between steps
centers = {}
for i, (title, stages, steps, out) in enumerate(BOXES):
    x = X0 + i * (W + GAP)
    ax.add_patch(FancyBboxPatch((x, BOT), W, TOP - BOT, boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc="white", ec=EDGE, lw=1.2))
    ax.text(x + 0.14, TOP - 0.24, title, fontsize=11, weight="bold", color=INK, va="center")
    if stages:
        ax.text(x + 0.14, TOP - 0.5, stages, fontsize=7.4, color=GREY, va="center")
    y = TOP - 0.72
    lp = 0.42 if i == 0 else 0.16          # box 1 leaves room on the left for its review loop
    for k, (who, text) in enumerate(steps):
        top = y - k * (SH + SG)
        ax.add_patch(FancyBboxPatch((x + lp, top - SH), W - lp - 0.16, SH, boxstyle="round,pad=0.01,rounding_size=0.06",
                                    fc=FILL[who], ec="none"))
        ax.text(x + lp + 0.14, top - SH / 2, text, fontsize=7.9, color=INK, va="center", linespacing=1.15)
        centers[(i, k)] = (x + lp, x + W - 0.16, top - SH, top)
        if k:
            ax.add_patch(FancyArrowPatch((x + (lp + W - 0.16) / 2, top + SG - 0.01), (x + (lp + W - 0.16) / 2, top + 0.01),
                                         arrowstyle="-|>", mutation_scale=9, lw=1.0, color=EDGE))
    ax.text(x + W / 2, BOT - 0.24, f"Out: {out}", fontsize=8.8, color=INK, ha="center", va="center", weight="bold")
    if i < 2:
        ax.add_patch(FancyArrowPatch((x + W + 0.03, TOP - 0.24), (x + W + GAP - 0.03, TOP - 0.24),
                                     arrowstyle="-|>", mutation_scale=14, lw=1.5, color=EDGE))


def side(i, k, right=True):
    l, r, b, t = centers[(i, k)]
    return (r if right else l, (b + t) / 2)


# box 1: we review the draft and send it back until it is right (left side)
p, q = side(0, 4, right=False), side(0, 3, right=False)
ax.add_patch(FancyArrowPatch((p[0] - 0.02, p[1]), (q[0] - 0.02, q[1]), connectionstyle="arc3,rad=-0.9",
                             arrowstyle="-|>", mutation_scale=9, lw=1.1, color=LOOP))
ax.text(q[0] + 0.06, (p[1] + q[1]) / 2, "adjust, redraft", fontsize=6.4, color=LOOP, va="center", ha="left")

# box 2: next batch until agreement holds
p, q = side(1, 3), side(1, 0)
ax.add_patch(FancyArrowPatch((p[0] + 0.02, p[1]), (q[0] + 0.02, q[1]), connectionstyle="arc3,rad=0.55",
                             arrowstyle="-|>", mutation_scale=9, lw=1.1, color=LOOP))
ax.text(q[0] + 0.12, q[1] - 0.95, "next\nbatch", fontsize=6.6, color=LOOP, va="center", ha="left")

# box 2 to box 1: codebook changes go back to the review
p, q = side(1, 3, right=False), side(0, 4)
ax.add_patch(FancyArrowPatch((p[0] - 0.02, p[1]), (q[0] + 0.02, q[1]), connectionstyle="arc3,rad=0.15",
                             arrowstyle="-|>", mutation_scale=10, lw=1.2, color=LOOP, linestyle=(0, (3, 2))))
ax.text(X0 + W + GAP / 2, p[1] + 0.42, "revise\ncode-\nbook", fontsize=6.2, color=LOOP, ha="center", va="center")

# key
for kx, (who, name) in zip((5.75, 6.95, 7.95), (("R", "researchers"), ("M", "model"), ("F", "fixed code"))):
    ax.add_patch(FancyBboxPatch((kx, 5.72), 0.22, 0.16, boxstyle="round,pad=0.01", fc=FILL[who], ec="none"))
    ax.text(kx + 0.3, 5.8, name, fontsize=8, va="center", color=INK)

fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
print("wrote", OUT)
