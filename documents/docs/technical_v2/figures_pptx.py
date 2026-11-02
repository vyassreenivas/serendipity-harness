"""The technical document's four figures as editable PowerPoint slides.

Usage: python figures_pptx.py OUT.pptx   (needs python-pptx)

One slide per figure, drawn with native shapes, text boxes and lines, so every
box, word and arrow can be edited in PowerPoint. Each slide repeats the
geometry of its PNG exactly: the same coordinates, text, line breaks, colours,
arrows and curves as figures.py (figures 1, 3 and 4) and ../source/tree.py
(figure 2), scaled to fill the slide; font sizes scale with the drawing. Curved
arrows are drawn as matplotlib draws them (a quadratic curve bent by the same
amount), as an open freeform line whose points can be edited. Figures 3 and 4
read their steps from process.json, like the PNGs.
"""
import json
import sys
import textwrap
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

FILL = {"us": "D7EBD5", "model": "FBE3C4", "program": "DCE6F2"}
EDGE, INK, GREY, LOOP, CHECK, NAVY = "4A4A4A", "1A1A1A", "666666", "8A3B12", "2F6B3A", "1F3A5F"
SQFILL, GFILL, MISFILL = "DCE6F2", "FFFFFF", "EFE3F3"
FONT = "DejaVu Sans"   # matplotlib's default font, so the slides look like the PNGs
SW, SH_, MARGIN = 13.333, 7.5, 0.4
PROCESS = json.loads(Path(__file__).with_name("process.json").read_text(encoding="utf-8"))


class Canvas:
    """Draws in a figure's own coordinates (y up), mapped onto the slide."""

    def __init__(self, slide, xlim, ylim, fig_w_in):
        self.s, (x0, x1), (y0, y1) = slide, xlim, ylim
        self.k = min((SW - 2 * MARGIN) / (x1 - x0), (SH_ - 2 * MARGIN) / (y1 - y0))
        self.ox = (SW - (x1 - x0) * self.k) / 2 - x0 * self.k
        self.oy = (SH_ - (y1 - y0) * self.k) / 2 + y1 * self.k
        self.font = self.k * (x1 - x0) / fig_w_in   # slide inches per figure inch

    def xy(self, x, y):
        return self.ox + x * self.k, self.oy - y * self.k

    def pt(self, size):
        return Pt(size * self.font)

    def rect(self, x, y, w, h, fill, edge=None, lw=1.0, rounding=0.06, pad=0.0):
        x, y, w, h = x - pad, y - pad, w + 2 * pad, h + 2 * pad
        sx, sy = self.xy(x, y + h)
        shp = self.s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(sx), Inches(sy),
                                      Inches(w * self.k), Inches(h * self.k))
        shp.adjustments[0] = min(0.5, (rounding + pad) / min(w, h))
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(fill)
        if edge:
            shp.line.color.rgb = RGBColor.from_string(edge)
            shp.line.width = Pt(lw * self.font)
        else:
            shp.line.fill.background()
        shp.shadow.inherit = False
        return shp

    def text(self, x, y, s, size, color=INK, bold=False, italic=False, ha="left", va="center", spacing=1.15):
        """Text placed as matplotlib places it: (x, y) is the anchor, ha and va say which side."""
        lines = s.split("\n")
        h = len(lines) * size * spacing * self.font / 72 + 0.04
        longest = max(len(line) for line in lines)
        w = max(0.3, longest * size * 0.62 * self.font / 72 + 0.1)
        sx, sy = self.xy(x, y)
        left = {"left": sx, "center": sx - w / 2, "right": sx - w}[ha]
        top = {"top": sy, "center": sy - h / 2, "bottom": sy - h}[va]
        tb = self.s.shapes.add_textbox(Inches(left), Inches(top), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = False
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = {"top": MSO_ANCHOR.TOP, "center": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}[va]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}[ha]
            p.line_spacing = spacing
            r = p.add_run()
            r.text = line
            f = r.font
            f.name, f.size, f.bold, f.italic = FONT, self.pt(size), bold, italic
            f.color.rgb = RGBColor.from_string(color)
        return tb

    def line(self, pts, color, lw, arrow=False, dash=False):
        """An open line through figure points; an arrowhead at the last point if arrow."""
        spts = [self.xy(x, y) for x, y in pts]
        fb = self.s.shapes.build_freeform(Inches(spts[0][0]), Inches(spts[0][1]), scale=1.0)
        fb.add_line_segments([(Inches(x), Inches(y)) for x, y in spts[1:]], close=False)
        shp = fb.convert_to_shape()
        shp.fill.background()
        shp.line.color.rgb = RGBColor.from_string(color)
        shp.line.width = Pt(lw * self.font)
        shp.shadow.inherit = False
        ln = shp.line._get_or_add_ln()
        if dash:
            ln.append(ln.makeelement(qn("a:prstDash"), {"val": "dash"}))
        if arrow:
            ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        return shp

    def arrow(self, p, q, color=EDGE, lw=1.0, rad=0.0, dash=False, head=True):
        """matplotlib's FancyArrowPatch with connectionstyle arc3: a quadratic curve bent by rad."""
        (x1, y1), (x2, y2) = p, q
        if not rad:
            return self.line([p, q], color, lw, arrow=head, dash=dash)
        cx, cy = (x1 + x2) / 2 + rad * (y2 - y1), (y1 + y2) / 2 - rad * (x2 - x1)
        pts = [((1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t * t * x2,
                (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t * t * y2) for t in (i / 24 for i in range(25))]
        return self.line(pts, color, lw, arrow=head, dash=dash)


def overview(c):
    boxes = [
        ("1  Build the codebook", "Stages 1 and 2", [
            ("us", "Read the literature; choose\nthe works to integrate"),
            ("us", "Pose the question; split it into\nsub-questions and groups"),
            ("us", "Choose the archival data"),
            ("model", "Draft codes from the chosen\npapers, each with its evidence"),
            ("us", "Review: codes fit their quotes\nand their literature"),
        ], "frozen codebook"),
        ("2  Code the interviews", "Stage 3", [
            ("model", "Code 25 new interviews;\nrecode earlier ones blind"),
            ("program", "Compare old and new\ncoding; list anomalies"),
            ("us", "Check each round's anomalies\nagainst the literature"),
            ("us", "Revise the codebook\nfrom papers read in full"),
            ("model", "When rounds settle: code\nthe whole corpus; we spot-check"),
        ], "coded interviews"),
        ("3  Analyse", "Stage 4", [
            ("program", "Count codes; trace anomalies\nacross versions"),
            ("us", "Study the anomalies no\npaper explains"),
            ("us", "Interpret and build theory"),
        ], "findings"),
    ]
    W, X0, GAP, TOP, BOT, SH, SG = 2.95, 0.12, 0.45, 5.25, 0.55, 0.62, 0.2
    centers = {}
    for i, (title, stages, steps, out) in enumerate(boxes):
        x = X0 + i * (W + GAP)
        c.rect(x, BOT, W, TOP - BOT, "FFFFFF", EDGE, 1.2, rounding=0.1, pad=0.02)
        c.text(x + 0.14, TOP - 0.24, title, 11, bold=True)
        c.text(x + 0.14, TOP - 0.5, stages, 7.4, color=GREY)
        lp = 0.42 if i == 0 else 0.16
        for k, (who, s) in enumerate(steps):
            top = TOP - 0.72 - k * (SH + SG)
            c.rect(x + lp, top - SH, W - lp - 0.16, SH, FILL[who], rounding=0.06, pad=0.01)
            c.text(x + lp + 0.14, top - SH / 2, s, 7.9)
            centers[(i, k)] = (x + lp, x + W - 0.16, top - SH, top)
            if k:
                xm = x + (lp + W - 0.16) / 2
                c.arrow((xm, top + SG - 0.01), (xm, top + 0.01), lw=1.0)
        c.text(x + W / 2, BOT - 0.24, f"Out: {out}", 8.8, bold=True, ha="center")
        if i < 2:
            c.arrow((x + W + 0.03, TOP - 0.24), (x + W + GAP - 0.03, TOP - 0.24), lw=1.5)

    def side(i, k, right=True):
        l, r, b, t = centers[(i, k)]
        return (r if right else l, (b + t) / 2)
    p, q = side(0, 4, False), side(0, 3, False)
    c.arrow((p[0] - 0.02, p[1]), (q[0] - 0.02, q[1]), color=LOOP, lw=1.1, rad=-0.9)
    c.text(q[0] + 0.06, (p[1] + q[1]) / 2, "adjust, redraft", 6.4, color=LOOP)
    p, q = side(1, 3), side(1, 0)
    c.arrow((p[0] + 0.02, p[1]), (q[0] + 0.02, q[1]), color=LOOP, lw=1.1, rad=0.55)
    c.text(q[0] + 0.12, q[1] - 0.95, "next\nround", 6.6, color=LOOP)
    p, q = side(1, 3, False), side(0, 4)
    c.arrow((p[0] - 0.02, p[1]), (q[0] + 0.02, q[1]), color=LOOP, lw=1.2, rad=0.15, dash=True)
    c.text(X0 + W + GAP / 2, p[1] + 0.42, "revise\ncode-\nbook", 6.2, color=LOOP, ha="center")
    x, y = 5.55, 5.8
    for kx, who in zip((x - 0.4, x + 1.0, x + 2.0), ("us", "model", "program")):
        c.rect(kx, y - 0.08, 0.22, 0.16, FILL[who], rounding=0.02, pad=0.01)
        c.text(kx + 0.3, y, {"us": "researchers", "model": "model", "program": "program"}[who], 8)


def tree(c):
    def box(cx, cy, w, h, fill, s, fs, color=INK, weight=False, ec=EDGE, italic=False):
        c.rect(cx - w / 2, cy - h / 2, w, h, fill, ec, 0.9, rounding=0.06, pad=0.02)
        if s:
            c.text(cx, cy, s, fs, color=color, bold=weight, italic=italic, ha="center")

    def line(x0, y0, x1, y1):
        c.arrow((x0, y0), (x1, y1), color="777777", lw=0.9, head=False)

    def panel(top, question, note, sqs, anomaly, label):
        c.text(0.15, top + 0.5, label, 9.6, color=NAVY, bold=True)
        box(5, top, 9.7, 0.62, NAVY, "", 9, ec=NAVY)
        c.text(5, top + 0.11, question, 8.8, color="FFFFFF", bold=True, ha="center")
        c.text(5, top - 0.15, note, 7.6, color="DDE5EF", italic=True, ha="center")
        n = len(sqs)
        step = 9.7 / n
        xs = [0.15 + step * (i + 0.5) for i in range(n)]
        w = min(1.55, step - 0.12)
        ysq, yg, yl = top - 1.05, top - 1.82, top - 0.5
        line(xs[0], yl, xs[-1], yl); line(5, top - 0.31, 5, yl)
        deepest = yg
        for x, (code, q, groups) in zip(xs, sqs):
            line(x, yl, x, ysq + 0.33)
            box(x, ysq, w, 0.66, SQFILL, "", 8)
            c.text(x, ysq + 0.18, code, 8.2, bold=True, ha="center")
            c.text(x, ysq - 0.1, q, 7.2, ha="center")
            last = yg - 0.38 * (len(groups) - 1)
            line(x, ysq - 0.33, x, last)
            for k, g in enumerate(groups):
                box(x, yg - 0.38 * k, min(1.3, w - 0.1), 0.3, GFILL, g, 7.6, weight=True)
            deepest = min(deepest, last)
        box(5, deepest - 0.45, 9.7, 0.34, MISFILL, anomaly, 7.6)

    panel(6.95, "Research question",
          "its kind (process, variance or conceptual)  ·  the state of theory  ·  deductive, inductive or abductive",
          [("Sub-question 1", "What is it?", ["definition", "kinds"]),
           ("Sub-question 2", "How does it\nhappen?", ["triggers", "actions"]),
           ("Sub-question 3", "What does it\nlead to?", ["results"]),
           ("Sub-question …", "one for each part\nof the question", ["groups"])],
          "anomaly group  ·  what no other group asks about", "a. The method, for any study")
    panel(3.4, "How does serendipity shape the entrepreneurial process, from the first idea to the developing venture?",
          "a process question, with a conceptual part  ·  intermediate theory  ·  abductive",
          [("SQ1", "What counts as\nserendipity?", ["1 definition", "2 type", "3 rival"]),
           ("SQ2", "What triggers it?", ["4 trigger"]),
           ("SQ3", "What do founders\nbring and do?", ["5 background", "6 mechanism"]),
           ("SQ4", "What does it change\nin the venture?", ["7 role", "8 outcome"]),
           ("SQ5", "When is it more\nor less likely?", ["9 condition"]),
           ("SQ6", "How do founders\ntell it?", ["10 account"])],
          "11 anomaly  ·  what no other group captures, for any sub-question", "b. Applied to serendipity")


def sizes(n):
    """Column width, box width and height, first box, wrap width and font size, as in figures.py."""
    return (1.6, 1.46, 0.9, 1.45, 21, 6.6) if n <= 6 else (1.18, 1.06, 0.9, 1.45, 17, 5.4)


def lanes(c, phase):
    steps = phase["steps"]
    n = len(steps)
    cw, bw, bh, x0, wrap, fs = sizes(n)
    rows = {"us": 2.4, "model": 1.3, "program": 0.2}
    width = x0 + 0.1 + n * cw
    for who, y in rows.items():
        c.rect(0.05, y - 0.08, width - 0.1, bh + 0.16, "F7F7F7", rounding=0.05)
        c.text(0.15, y + bh / 2, {"us": "Researchers", "model": "Model", "program": "Program"}[who], 8, bold=True)
    prev = None
    for k, s in enumerate(steps):
        x = x0 + k * cw
        y = rows[s["who"]]
        c.rect(x, y, bw, bh, FILL[s["who"]], CHECK if s.get("check") else None, 1.6, rounding=0.06, pad=0.01)
        c.text(x + 0.06, y + bh - 0.1, str(k + 1), 7, color=GREY, bold=True, va="top")
        c.text(x + bw / 2, y + bh / 2 - 0.04, "\n".join(textwrap.wrap(s["what"], wrap)), fs, ha="center", spacing=1.08)
        if s.get("check"):
            c.text(x + bw - 0.06, y + bh - 0.1, s.get("label", "we decide"), 5.2, color=CHECK, bold=True, ha="right", va="top")
        if prev:
            px, py = prev
            c.arrow((px + bw, py + bh / 2), (x, y + bh / 2), lw=0.9)
        prev = (x, y)
    c.text(x0 + n * cw - 0.1, -0.28, f"Out: {phase['out']}", 8, bold=True, ha="right")
    c.text(x0, 3.42, phase["containers"], 7, color=GREY, italic=True)


def build(out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(SW), Inches(SH_)
    blank = prs.slide_layouts[6]
    overview(Canvas(prs.slides.add_slide(blank), (0, 10), (0, 6.1), 10))
    tree(Canvas(prs.slides.add_slide(blank), (0, 10), (0.1, 7.55), 10))
    for phase in PROCESS["phases"]:
        cw, _, _, x0, _, _ = sizes(len(phase["steps"]))
        width = x0 + 0.1 + len(phase["steps"]) * cw
        lanes(Canvas(prs.slides.add_slide(blank), (0, width), (-0.45, 3.55), width * 0.92), phase)
    prs.save(out)


if __name__ == "__main__":
    build(sys.argv[1])
    print("wrote", sys.argv[1])
