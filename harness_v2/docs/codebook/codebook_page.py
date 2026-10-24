"""Build the interactive codebook page from the review workbook.

Usage: python codebook_page.py codebook_review.xlsx [codebook.html]

The page shows the coder view on the left (11 groups, one short line per code)
and the full entry for the selected code on the right: description, when to
code it, example, the nearest look-alike, and the evidence sentence from each
supporting paper with its page and link. Wording comes from the workbook (so
edits there show here after a rebuild); evidence comes from the same functions
the workbook uses. Holds codes, our own wording and one-sentence quotes from
the papers; no interview text.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from export import GROUPS, MISFIT
from workbook import SQTEXT, chooser, evidence_for, load_draft, state_from_workbook

TEMPLATE = Path(__file__).with_name("codebook_page_template.html")


def build(xlsx: str, out: str) -> None:
    state = state_from_workbook(xlsx)
    draft = load_draft()
    groups, codes = [], []
    for gi, (name, sq, asks) in enumerate(GROUPS, 1):
        groups.append({"n": gi, "name": name, "asks": asks,
                       "sq": SQTEXT[sq] if sq == "all" else f"{sq}: {SQTEXT[sq]}"})
        if name == "anomaly":
            for m in MISFIT["codes"]:
                codes.append({"id": m["id"], "group": name, "status": "core", "label": m["label"],
                              "description": "", "when": m["applies_when"], "example": "",
                              "notwhen": m["does_not_apply_when"], "evidence": [],
                              "note": "Anomaly code, fixed in Stage 1. Use it when no core code in a group fits."})
            continue
        ids = sorted((i for i in draft if draft[i]["group"] == name),
                     key=lambda i: (state[i]["Status"] != "core", int(i.split("-")[1])))  # core first
        for cid in ids:
            s = state[cid]
            if s["Status"] == "reject":
                continue
            ev = []
            for e in evidence_for(draft[cid]):
                ev.append({"cite": e["short"], "title": e["title"], "venue": e["venue"], "url": e["url"],
                           "page": e["quote"]["pdf_page"] if e["quote"] else None,
                           "text": e["quote"]["text"] if e["quote"] else "",
                           "close": bool(e.get("close")), "none": bool(e.get("none")), "chosen": chooser(e)})
            codes.append({"id": cid, "group": name, "status": s["Status"], "label": s["Label"],
                          "description": s["Description"], "when": s["Code it when"],
                          "example": s["Example (made up)"], "notwhen": s["Not when"], "evidence": ev,
                          "note": "New: from a paper read after the draft." if s["Reason"].startswith("New") else ""})
    data = {"built": date.today().isoformat(), "source": Path(xlsx).name, "groups": groups, "codes": codes}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", payload)
    Path(out).write_text(html, encoding="utf-8")
    core = sum(c["status"] == "core" for c in codes)
    print(f"wrote {out}: {core} core (incl. anomaly), {len(codes) - core} reference, "
          f"{sum(len(c['evidence']) for c in codes)} evidence sentences, {len(html) // 1024} KB")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "codebook.html")
