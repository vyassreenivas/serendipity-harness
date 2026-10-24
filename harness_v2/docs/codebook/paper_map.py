"""Write the code-to-paper map: every code with its papers, and every paper with its codes.

Usage: python paper_map.py codebook_review.xlsx codebook_paper_map.xlsx

Two sheets, built from the same records as the review workbook:
  By code   one row per code (core and reference; rejected codes left out):
            group, code, status, label, number of papers, the papers
  By paper  one row per paper: citation, title, number of codes, its core
            codes, all its codes
A paper counts for a code when the code was drawn from it (the draft and the
papers read after it). Where reading found no sentence in that paper that
states a core code, the paper is still listed, marked with an asterisk.
"""
import sys
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from export import GROUPS
from workbook import evidence_for, load_draft, state_from_workbook

FONT, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="1F3A5F")
WRAP = Alignment(wrap_text=True, vertical="top")
ORDER = {name: i for i, (name, _, _) in enumerate(GROUPS)}


def sheet(ws, cols, rows):
    for j, (name, width) in enumerate(cols, 1):
        c = ws.cell(row=1, column=j, value=name)
        c.font, c.fill, c.alignment = BOLD, FILL, WRAP
        ws.column_dimensions[c.column_letter].width = width
    for i, r in enumerate(rows, 2):
        for j, v in enumerate(r, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.font, c.alignment = FONT, WRAP
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions


def build(xlsx: str, out: str) -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    by_code, papers = [], {}
    paper_codes = defaultdict(list)
    ids = sorted((i for i in draft if state[i]["Status"] != "reject"),
                 key=lambda i: (ORDER.get(draft[i]["group"], 99), state[i]["Status"] != "core", int(i.split("-")[1])))
    for cid in ids:
        s = state[cid]
        ev = evidence_for(draft[cid])
        cites = []
        for e in ev:
            key = e["short"] + e["url"]
            papers.setdefault(key, e)
            star = "*" if e.get("none") else ""
            cites.append(e["short"] + star)
            paper_codes[key].append((cid, s["Label"], s["Status"]))
        by_code.append([draft[cid]["group"], cid, s["Status"], s["Label"], len(ev), "; ".join(cites)])
    by_paper = []
    for key, e in sorted(papers.items(), key=lambda kv: (-len(paper_codes[kv[0]]), kv[1]["short"].lower())):
        codes = paper_codes[key]
        core = [f"{c} {l}" for c, l, st in codes if st == "core"]
        by_paper.append([e["short"], e["title"], len(codes), "; ".join(core),
                         "; ".join(f"{c} {l}" for c, l, _ in codes)])
    wb = Workbook()
    ws = wb.active; ws.title = "By code"
    sheet(ws, [("Group", 12), ("Code ID", 14), ("Status", 10), ("Code", 34), ("Papers", 8), ("Papers it comes from", 90)], by_code)
    sheet(wb.create_sheet("By paper"), [("Paper", 26), ("Title", 50), ("Codes", 7),
                                        ("Core codes from this paper", 60), ("All codes from this paper", 90)], by_paper)
    note = wb.create_sheet("Read me")
    for i, t in enumerate([
        "Code-to-paper map for the serendipity codebook (draft, not frozen).",
        "By code: every code (core and reference; rejected codes left out) and every paper it was drawn from.",
        "By paper: every paper and every code drawn from it, core codes listed first in their own column.",
        "An asterisk (*) after a paper means reading found no sentence in that paper that states the code.",
        "Evidence sentences, pages and links for each code-paper pair are in codebook_review.xlsx (Evidence sheet).",
    ], 1):
        note.cell(row=i, column=1, value=t).font = FONT
    note.column_dimensions["A"].width = 110
    wb.move_sheet("Read me", offset=-2)
    wb.save(out)
    print(f"wrote {out}: {len(by_code)} codes, {len(by_paper)} papers")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
