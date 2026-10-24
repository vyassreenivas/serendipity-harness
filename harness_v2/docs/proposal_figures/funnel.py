"""Draw the harness as a funnel, for the proposal (not the technical document).

Usage: python funnel.py funnel.png   (needs matplotlib)
Part A is a row of stages from the question to a codebook. Part B is a funnel:
the whole corpus at the top, coded by the model with the frozen codebook, and
the narrow anomaly residue at the bottom, coded by people. The calibration loop
and the held-out test sit beside the funnel.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

OUT = sys.argv[1]
FILL = {"people": "#D7EBD5", "model": "#FBE3C4", "code": "#DCE6F2", "out": "#1F3A5F", "input": "#FFFFFF"}
EDGE = "#4A4A4A"
LOOP = "#8A3B12"

fig, ax = plt.subplots(figsize=(10.25, 8.6))
ax.set_xlim(0, 10.25); ax.set_ylim(-0.35, 8.25); ax.axis("off")


def box(x, y, title, who, kind, n=None, w=1.8, h=0.95, fs=7.6):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=FILL[kind], ec=EDGE if kind != "out" else FILL[kind],
                                lw=0.9))
    color = "white" if kind == "out" else "#1A1A1A"
    if who:
        ax.text(x, y + 0.12, title, ha="center", va="center", fontsize=fs, weight="bold", color=color)
        ax.text(x, y - 0.3, who, ha="center", va="center", fontsize=7.2, style="italic", color=color)
    else:
        ax.text(x, y, title, ha="center", va="center", fontsize=fs + 0.6, weight="bold", color=color)


def arrow(pts, text=None, tpos=None, color="#333333", ha="center"):
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        ax.plot([x0, x1], [y0, y1], color=color, lw=1.2)
    ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2))
    if text:
        ax.text(*tpos, text, fontsize=7.3, color=color, ha=ha, va="center", style="italic",
                bbox=dict(fc="white", ec="none", pad=1))


# ---------- Part A: from the question to a codebook ----------
X = [1.1, 3.0, 4.9, 6.8, 8.75]
ya = 6.85
ax.text(0.2, 8.15, "Part A  From the question to a codebook", fontsize=9.5, weight="bold", color="#333333", va="center")
box(X[0], 7.75, "Research question", "", "input", h=0.32, fs=7.2)
box(X[1], 7.75, "Papers", "", "input", h=0.32, fs=7.2)
box(X[0], ya, "1  Break the question\ninto sub-questions", "Researchers", "people", n=1)
box(X[1], ya, "2  Choose papers for\neach sub-question", "Researchers; checked", "people", n=2)
box(X[2], ya, "3  Read papers for\ncandidate codes", "Model; checked", "model", n=3)
box(X[3], ya, "4  Merge into a\ndraft codebook", "Model; checked", "model", n=4)
box(X[4], ya, "5  Review the\ndraft codebook", "Researchers", "people", n=5)
for i in (0, 1):
    arrow([(X[i], 7.59), (X[i], ya + 0.475)])
for a in range(4):
    arrow([(X[a] + 0.9, ya), (X[a + 1] - 0.9, ya)])

# ---------- Part B: the funnel ----------
CX, TOP, BOT, TW, BW = 3.55, 5.05, 0.75, 5.7, 1.7   # centre, top and bottom y, top and bottom widths


def half(y):
    return (BW + (TW - BW) * (y - BOT) / (TOP - BOT)) / 2


def layer(y0, y1, kind, n=None):
    pts = [(CX - half(y1), y1), (CX + half(y1), y1), (CX + half(y0), y0), (CX - half(y0), y0)]
    ax.add_patch(Polygon(pts, closed=True, fc=FILL[kind], ec=EDGE, lw=0.9))


ax.text(0.2, 5.45, "Part B  Coding the interviews: a funnel", fontsize=9.5, weight="bold", color="#333333", va="center")
L1, L2, L3, L4 = (4.35, 5.05), (2.85, 4.27), (1.85, 2.77), (0.75, 1.77)
layer(*L1, "input")
ax.text(CX, 4.7, "The whole corpus: 1,972 founder interviews", ha="center", va="center", fontsize=8.6, weight="bold")
layer(*L2, "model", n=8)
ax.text(CX, 3.78, "8  The model codes every interview\ndeductively, with the frozen codebook", ha="center", va="center",
        fontsize=8.2, weight="bold")
ax.text(CX, 3.17, "Model; researchers spot-check about 5%", ha="center", va="center", fontsize=7.2, style="italic")
layer(*L3, "input")
ax.text(CX, 2.38, "Anomaly pool: what\nno code can hold", ha="center", va="center", fontsize=8.2, weight="bold")
layer(*L4, "people", n=8)
ax.text(CX, 1.4, "People code\nit abductively", ha="center", va="center", fontsize=8, weight="bold")
ax.text(CX, 0.98, "Researchers", ha="center", va="center", fontsize=7.2, style="italic")

# what comes out of the funnel
box(0.95, 2.05, "CODED CORPUS\n+ agreement\nreport", "", "out", w=1.55, h=1.0, fs=7.8)
arrow([(CX - half(3.5), 3.5), (0.95, 3.5), (0.95, 2.55)])
ax.text(CX + 1.4, 1.2, "Findings, revised codes, or rarely\na targeted recode.  No loop over\nthe full corpus.",
        fontsize=7.4, va="center", ha="left", style="italic", color="#333333")
arrow([(CX + half(1.25), 1.25), (CX + 1.33, 1.25)], color="#333333")

# ---------- beside the funnel: calibration loop and held-out test ----------
CC, CW = 8.75, 1.85
box(CC, 5.3, "CODEBOOK\nversion n", "", "out", w=CW, h=0.62, fs=8.2)
box(CC, 4.25, "6  Calibration round:\n25 to 50 interviews", "Researchers and model", "people", n=6, w=CW)
box(CC, 3.0, "7  Compare coders;\nanalyse anomalies; revise", "Fixed code; researchers", "code", n=7, w=CW)
box(CC, 1.62, "8  Held-out test on\n30 to 50 interviews", "Researchers and model", "people", n=8, w=CW)
arrow([(X[4], ya - 0.475), (CC, 5.61)])
arrow([(CC, 4.99), (CC, 4.725)])
arrow([(CC, 3.775), (CC, 3.475)])
arrow([(CC + CW / 2, 3.0), (9.92, 3.0), (9.92, 5.3), (CC + CW / 2, 5.3)], color=LOOP)
ax.text(10.07, 4.15, "new version, until the four stopping\nconditions hold (about five rounds)",
        fontsize=7.1, color=LOOP, ha="center", va="center", style="italic", rotation=90)
arrow([(CC, 2.525), (CC, 2.095)], "codebook frozen", (CC + 0.08, 2.31), ha="left")
arrow([(CC - CW / 2, 1.62), (7.3, 1.62), (7.3, 3.35), (CX + half(3.35), 3.35)])
ax.text(7.2, 2.2, "if agreement\nholds", fontsize=7.1, ha="right", va="center", style="italic", color="#333333")
arrow([(CX + half(4.5), 4.5), (CC - CW / 2, 4.5)], "a fresh sample\nfor each round", (7.0, 4.5))
arrow([(CC - CW / 2, 2.85), (CX + half(2.4) + 0.05, 2.4)], color="#777777")
ax.text(6.0, 2.78, "anomalies", fontsize=7.1, color="#777777", ha="center", va="center", style="italic", rotation=-10)

# legend
items = [("people", "Researchers decide"), ("model", "Model proposes; fixed code checks"),
         ("code", "Fixed code"), ("out", "What comes out")]
for i, (k, t) in enumerate(items):
    x = [0.25, 2.45, 5.35, 7.1][i]
    ax.add_patch(FancyBboxPatch((x, -0.25), 0.26, 0.24, boxstyle="round,pad=0.01", fc=FILL[k], ec=EDGE, lw=0.7))
    ax.text(x + 0.36, -0.13, t, fontsize=7.6, va="center")

fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved", OUT)
