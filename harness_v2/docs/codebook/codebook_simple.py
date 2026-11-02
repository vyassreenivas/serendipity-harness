"""Export the codebook (both levels) as JSON for codebook_simple.js.

Usage: python codebook_simple.py codebook_review.xlsx codebook_simple.json [CODEBOOK_JSON]
       node codebook_simple.js codebook_simple.json codebook_simple.docx

The codebook as a reader sees it, not a coding guide. Codes are numbered by
group (2.3 is the third code of group 2). Level 1: for each group, its
sub-question and question, and for each code its label, what it captures (the
workbook's Description) and the papers that state it; the group's anomaly code
last. Level 2: the definitions, rival explanations, types and judgments, each
with its rule over level-1 codes. The coding page holds the coders' instructions.
Wording comes from the workbook; the levels come from harness/codebook/levels.json.
With a later codebook version (CODEBOOK_JSON), its added and revised codes are
included and marked with the version that added them; an inductive code says
so in place of papers.
"""
import json
import sys
from datetime import date
from pathlib import Path

from export import LEVELS
from levels import NEW, SUB_QUESTIONS, level1, level1_ids, numbers, rule_equation, rule_evidence
from version import apply
from workbook import evidence_for, load_draft, state_from_workbook

KINDS = [("definition", "Definitions of serendipity", "D"), ("rival", "Rival explanations (Busch 2024, p. 29)", "R"),
         ("type", "Types (after Yaqub 2018)", "T"), ("judgment", "Decided by the researchers", "J")]


def cites(ev, n=3):
    shorts = list(dict.fromkeys(e["short"] for e in ev))
    return "; ".join(shorts[:n]) + (f"; + {len(shorts) - n} more" if len(shorts) > n else "")


def build(xlsx: str, out: str, version_file: str = "") -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    version = apply(state, draft, version_file) if version_file else "1.0"
    ticked = set(level1_ids(state, draft))
    ev = {c: [e for e in evidence_for(draft[c]) if (e["chosen"] or draft[c].get("unread")) and not e.get("none")]
          for c in ticked}
    added = lambda c: f" (added in {draft[c]['added_in']})" if draft[c].get("added_in") else ""
    groups, num = [], numbers(state, draft)
    for gi, g in enumerate(level1(state, draft), 1):
        p = g["pick_one"]
        entry = lambda c: {"no": num[c], "id": c, "label": state[c]["Label"] + added(c), "captures": state[c]["Description"],
                           "papers": cites(ev[c]) or "No paper yet: an inductive code, from the interviews",
                           "n_papers": len({e["short"] for e in ev[c]})}
        groups.append({"no": gi, "name": g["name"], "sq": g["sq"], "sq_text": SUB_QUESTIONS[g["sq"]], "asks": g["asks"],
                       "pick_one": {"name": p["name"], "asks": p["asks"], "options": [entry(c) for c in p["codes"]]} if p else None,
                       "codes": [entry(c) for c in g["codes"]],
                       "anomaly": {"no": f"{gi}.A", "id": g["anomaly"]["id"], "captures": g["anomaly"]["applies_when"]} if g["anomaly"] else None})
    label = {c: state[c]["Label"] for c in draft}
    rule = lambda r: rule_equation(r, label, num)

    level2 = []
    for kind, title, letter in KINDS:
        rows = [r for r in LEVELS["level2"] if r["kind"] == kind]
        level2.append({"part": title, "rows": [{"no": f"{letter}{k}", "name": r["name"], "in_short": r["in_short"],
                                                "rule": rule(r) if kind != "judgment" else "Decided by the researchers, with a written reason",
                                                "papers": cites(rule_evidence(r, draft))} for k, r in enumerate(rows, 1)]})
    sq = {}
    for g in groups:
        sq.setdefault(g["sq"], {"sq": g["sq"], "text": g["sq_text"], "groups": [], "codes": 0})
        sq[g["sq"]]["groups"].append(f"{g['no']}. {g['name']}")
        sq[g["sq"]]["codes"] += len(g["codes"]) + (len(g["pick_one"]["options"]) if g["pick_one"] else 0)
    data = {"version": version, "built": date.today().isoformat(), "source": xlsx, "structure": list(sq.values()),
            "level1": groups, "level2": level2,
            "new": {"no": f"{len(groups) + 1}.A", "id": NEW["id"], "captures": NEW["applies_when"]},
            "counts": {"level1": len(ticked), "groups": len(groups), "anomaly": sum(1 for g in groups if g["anomaly"]) + 1,
                       "level2": len(LEVELS["level2"])}}
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {out}: {data['counts']['level1']} level-1 codes in {len(groups)} groups, "
          f"{data['counts']['anomaly']} anomaly codes, {data['counts']['level2']} level-2 items")


if __name__ == "__main__":
    build(*sys.argv[1:4])
