"""Save codebook 1.0's evidence in the form later versions use.

Usage: python evidence_v1.py codebook_review.xlsx ../../../harness/codebook/evidence_v1.0.json

For each core code, and each level-2 item, the papers whose sentence (chosen by
reading) states it: the sentence, its PDF page, and the paper's reference. Papers
linked to a code where reading found no sentence that states it are listed
under "linked_only", so the record shows them too. The same records as
code_sources.html, in one file the reviewer pages read.
"""
import json
import sys
from pathlib import Path

from export import LEVELS
from levels import level1, rule_evidence
from workbook import evidence_for, load_draft, state_from_workbook


def entry(e: dict) -> dict:
    q = e["quote"]
    return {"paper": q["passage_id"].split(":")[0], "short": e["short"], "title": e["title"],
            "url": e["url"], "page": q["pdf_page"], "page_kind": "pdf", "quote": q["text"],
            **({"leans": True} if e.get("close") else {})}


def build(xlsx: str, out: str) -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    codes, linked = {}, {}
    for g in level1(state, draft):
        for c in (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]:
            ev = evidence_for(draft[c])
            codes[c] = [entry(e) for e in ev if e["chosen"] and not e.get("none") and e["quote"]]
            linked[c] = [e["short"] for e in ev if not (e["chosen"] and not e.get("none") and e["quote"])]
    level2 = {r["id"]: [entry(e) for e in rule_evidence(r, draft) if e.get("quote")] for r in LEVELS["level2"]}
    Path(out).write_text(json.dumps({
        "about": "Codebook 1.0: for each code, the papers whose sentence, chosen by reading, states it, with "
                 "the PDF page. 'linked_only' lists papers linked to a code where no sentence states it. "
                 "Written by harness_v2/docs/codebook/evidence_v1.py from the review workbook.",
        "codebook": "1.0", "codes": codes, "linked_only": linked, "level2": level2},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}: {sum(map(len, codes.values()))} sentences for {len(codes)} codes, "
          f"{sum(map(len, linked.values()))} links with no sentence, {len(level2)} level-2 items")


if __name__ == "__main__":
    build(*sys.argv[1:3])
