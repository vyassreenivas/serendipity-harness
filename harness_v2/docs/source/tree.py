"""Draw Stage 1: from a research question to sub-questions to analysis groups.

Usage: python tree.py tree.png   (needs matplotlib)
Panel a is the general method; panel b is the same method applied to serendipity.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = sys.argv[1]
INK, EDGE, NAVY = "#1A1A1A", "#4A4A4A", "#1F3A5F"
SQFILL, GFILL, MISFILL = "#DCE6F2", "#FFFFFF", "#EFE3F3"

fig, ax = plt.subplots(figsize=(10, 7.45))
ax.set_xlim(0, 10); ax.set_ylim(0.1, 7.55); ax.axis("off")


def box(cx, cy, w, h, fill, text, fs, color=INK, weight="normal", ec=EDGE, style="normal"):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                fc=fill, ec=ec, lw=0.9))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=color, weight=weight, style=style)


def line(x0, y0, x1, y1):
    ax.plot([x0, x1], [y0, y1], color="#777777", lw=0.9, zorder=0)


def tree(top, question, note, sqs, anomaly, label):
    """One panel. top is the y of the question box; sqs is [(code, question, [groups])]."""
    ax.text(0.15, top + 0.5, label, ha="left", va="center", fontsize=9.6, weight="bold", color=NAVY)
    box(5, top, 9.7, 0.62, NAVY, "", 9, ec=NAVY)
    ax.text(5, top + 0.11, question, ha="center", va="center", fontsize=8.8, color="white", weight="bold")
    ax.text(5, top - 0.15, note, ha="center", va="center", fontsize=7.6, color="#DDE5EF", style="italic")
    n = len(sqs)
    step = 9.7 / n
    xs = [0.15 + step * (i + 0.5) for i in range(n)]
    w = min(1.55, step - 0.12)
    ysq, yg = top - 1.05, top - 1.82
    yl = top - 0.5
    line(xs[0], yl, xs[-1], yl); line(5, top - 0.31, 5, yl)
    deepest = yg
    for x, (code, q, groups) in zip(xs, sqs):
        line(x, yl, x, ysq + 0.33)
        box(x, ysq, w, 0.66, SQFILL, "", 8)
        ax.text(x, ysq + 0.18, code, ha="center", va="center", fontsize=8.2, weight="bold", color=INK)
        ax.text(x, ysq - 0.1, q, ha="center", va="center", fontsize=7.2, color=INK)
        last = yg - 0.38 * (len(groups) - 1)
        line(x, ysq - 0.33, x, last)
        for k, g in enumerate(groups):
            box(x, yg - 0.38 * k, min(1.3, w - 0.1), 0.3, GFILL, g, 7.6, weight="bold")
        deepest = min(deepest, last)
    ym = deepest - 0.45
    box(5, ym, 9.7, 0.34, MISFILL, anomaly, 7.6)
    return ym


# a. the general method
tree(6.95, "Research question",
     "its kind (process, variance or conceptual)  ·  the state of theory  ·  deductive, inductive or abductive",
     [("Sub-question 1", "What is it?", ["definition", "kinds"]),
      ("Sub-question 2", "How does it\nhappen?", ["triggers", "actions"]),
      ("Sub-question 3", "What does it\nlead to?", ["results"]),
      ("Sub-question …", "one for each part\nof the question", ["groups"])],
     "anomaly group  ·  what no other group asks about", "a. The method, for any study")

# b. applied to serendipity
tree(3.4, "How does serendipity shape the entrepreneurial process, from the first idea to the developing venture?",
     "a process question, with a conceptual part  ·  intermediate theory  ·  abductive",
     [("SQ1", "What counts as\nserendipity?", ["1 definition", "2 type", "3 rival"]),
      ("SQ2", "Where does it happen,\nand what sets it off?", ["4 trigger"]),
      ("SQ3", "What do founders\nbring and do?", ["5 background", "6 mechanism"]),
      ("SQ4", "What does it change\nin the venture?", ["7 role", "8 outcome"]),
      ("SQ5", "When is it more\nor less likely?", ["9 condition"]),
      ("SQ6", "How do founders\ntell it?", ["10 account"])],
     "11 anomaly  ·  what no other group captures, for any sub-question", "b. Applied to serendipity")

fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved", OUT)
