"""Draw how the codebook is built: groups, all codes and core codes.

Usage: python codebook_map.py codebook_map.png   (needs matplotlib)
Top: papers become candidate codes, candidate codes become drafted codes
sorted into the groups from Stage 1, and the researchers mark each drafted
code core, reference or reject. Anomaly codes come last, one per group, once
the core codes are set. Bottom: one group worked through.
Colours match Figure 1: green researchers, orange model, blue both.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = sys.argv[1]
FILL = {"people": "#D7EBD5", "model": "#FBE3C4", "both": "#DCE6F2", "ref": "#ECECEC", "rej": "#F6D6D2",
        "group": "#F3F0FA"}
EDGE, INK, GREY = "#4A4A4A", "#1A1A1A", "#666666"

fig, ax = plt.subplots(figsize=(10, 5.6))
ax.set_xlim(0, 10); ax.set_ylim(0, 5.6); ax.axis("off")


def box(x, y, w, h, kind, lines, sizes, weights=None, styles=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=FILL[kind], ec=EDGE, lw=1.0))
    n = len(lines)
    for i, (t, s) in enumerate(zip(lines, sizes)):
        yy = y + h - (i + 0.5) * h / n
        ax.text(x + w / 2, yy, t, ha="center", va="center", fontsize=s, color=INK,
                weight=(weights or ["normal"] * n)[i], style=(styles or ["normal"] * n)[i])


def arrow(x1, y1, x2, y2, dashed=False, color=EDGE):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11, lw=1.1, color=color,
                                 linestyle=(0, (3, 2)) if dashed else "-"))


# ---- the groups from Stage 1, used as sorting bins
box(2.05, 4.75, 4.3, 0.6, "group", ["11 groups from Stage 1", "10 asked of every episode, plus anomaly"],
    [9, 7.6], ["bold", "normal"])

# ---- top row: papers to the codebook
Y, H = 2.7, 1.55
box(0.1, Y, 1.55, H, "model", ["113 papers", "read one by one", "Model; fixed code", "checks passages"],
    [10, 7.6, 7.2, 7.2], ["bold", "normal", "normal", "normal"], [None, None, "italic", "italic"])
box(2.05, Y, 1.85, H, "model", ["1,893 candidate", "codes", "each cites its passages", "Model"],
    [10, 10, 7.4, 7.2], ["bold", "bold", "normal", "normal"], [None, None, None, "italic"])
box(4.3, Y, 2.05, H, "model", ["369 drafted codes", "the All codes sheet", "same idea merged within a", "group; 94 off-topic set aside"],
    [10, 7.8, 7.2, 7.2], ["bold", "normal", "normal", "normal"])
arrow(1.67, Y + H / 2, 2.03, Y + H / 2)
arrow(3.92, Y + H / 2, 4.28, Y + H / 2)
arrow(3.0, 4.73, 3.0, Y + H + 0.03)
arrow(5.3, 4.73, 5.3, Y + H + 0.03)
ax.text(3.08, 4.5, "sorted into a group", fontsize=7, color=GREY, ha="left")

# ---- researchers' decision: three statuses
sx, sw = 6.72, 1.5
box(sx, Y + 1.07, sw, 0.48, "people", ["45 core", "applied to every episode"], [9, 6.4], ["bold", "normal"])
box(sx, Y + 0.53, sw, 0.48, "ref", ["314 reference", "kept; used for anomalies"], [9, 6.0], ["bold", "normal"])
box(sx, Y, sw, 0.48, "rej", ["10 reject", "duplicates"], [9, 6.8], ["bold", "normal"])
ax.text(sx + sw / 2, Y - 0.2, "Researchers decide", fontsize=7.4, style="italic", color=INK, ha="center")
arrow(6.37, Y + H / 2, 6.78, Y + 1.31)
arrow(6.37, Y + H / 2, 6.78, Y + 0.77)
arrow(6.37, Y + H / 2, 6.78, Y + 0.24)

# ---- the codebook coders use
box(8.55, Y + 0.3, 1.4, 1.25, "both", ["Codebook", "55 codes", "in 11 groups", "45 core + 10 anomaly"],
    [10, 9, 7.6, 6.4], ["bold", "bold", "normal", "normal"])
arrow(sx + sw + 0.02, Y + 1.31, 8.53, Y + 1.1)
# anomaly codes come last: written once the core codes are set
box(8.55, 4.5, 1.4, 0.72, "group", ["+ 10 anomaly codes", "one per group, for what", "its core codes miss"],
    [7.0, 6.6, 6.6], ["bold", "normal", "normal"])
arrow(sx + sw + 0.02, Y + 1.45, 8.53, 4.75)
arrow(9.25, 4.48, 9.25, Y + 1.57)

# ---- bottom: one group worked through
ax.plot([0.1, 9.95], [2.05, 2.05], color="#BBBBBB", lw=0.8)
ax.text(0.1, 1.78, "One group worked through: Trigger, “What unexpected event started it?”", fontsize=9,
        weight="bold", color=INK, ha="left")
core = ["Something odd\nwas noticed", "A mistake or\naccident", "A chance\nmeeting", "A passing\nremark",
        "An unasked-for\noffer or request", "An unexpected\nmarket signal"]
cw, cg, cy, ch = 1.06, 0.07, 0.55, 0.85
for i, t in enumerate(core):
    box(0.1 + i * (cw + cg), cy, cw, ch, "people", [t], [6.6], ["bold"])
ax.text(0.1, 0.28, "6 core codes: coders mark each one present or absent in every episode", fontsize=7.4, color=INK,
        ha="left")
box(7.0, cy, 1.4, ch, "ref", ["21 reference", "codes", "e.g. key person", "arrives at the right time"],
    [8, 8, 6.4, 6.4], ["bold", "bold", "normal", "normal"])
box(8.55, cy, 1.4, ch, "group", ["ANO-TRG", "an unexpected start", "no core code names"], [8.6, 6.8, 6.8],
    ["bold", "normal", "normal"])
ax.text(7.7, 0.28, "kept on record", fontsize=7.2, color=GREY, ha="center")
ax.text(9.25, 0.28, "anomaly code", fontsize=7.2, color=GREY, ha="center")

fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
print("wrote", OUT)
