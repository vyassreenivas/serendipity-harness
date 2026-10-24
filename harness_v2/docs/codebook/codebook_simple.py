"""Export the short codebook (core and anomaly codes only) as JSON for codebook_simple.js.

Usage: python codebook_simple.py codebook_review.xlsx codebook_simple.json
       node codebook_simple.js codebook_simple.json codebook_simple.docx

The short codebook is what coders read: for each group, its question, its core
codes (label, code it when, example, not when, papers) and its anomaly code.
Wording comes from the Codebook sheet of the workbook, so it follows every edit.
"""
import json
import sys
from datetime import date

from export import DEFINITIONS, GROUPS, MISFIT as ANOMALY
from workbook import SQTEXT, cite, evidence_for, load_draft, state_from_workbook


def build(xlsx: str, out: str) -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    anomaly = {m.get("overflows_from") or "new": m for m in ANOMALY["codes"]}
    groups = []
    for gi, (name, sq, asks) in enumerate(GROUPS, 1):
        if name == "anomaly":
            continue
        codes = []
        for cid in sorted((i for i in draft if draft[i]["group"] == name), key=lambda i: int(i.split("-")[1])):
            s = state[cid]
            if s["Status"] != "core":
                continue
            papers = sum(1 for e in evidence_for(draft[cid]) if not e.get("none"))
            codes.append({"id": cid, "label": s["Label"], "when": s["Code it when"],
                          "example": s["Example (made up)"], "notwhen": s["Not when"], "papers": papers})
        a = anomaly.get(name)
        groups.append({"n": gi, "name": name, "asks": asks, "sq": SQTEXT.get(sq, ""), "codes": codes,
                       "anomaly": {"id": a["id"], "when": a["applies_when"], "notwhen": a["does_not_apply_when"]} if a else None})
    new = anomaly.get("new") or next(m for m in ANOMALY["codes"] if m["id"].endswith("NEW"))
    defs = [{"id": d["id"], "name": d["name"], "in_short": d["in_short"], "papers": len({cite(q["passage_id"].split(":")[0])["short"] for q in d["evidence"]}),
             "needs": [state[cid]["Label"] for cid, _ in d["needs"]]} for d in DEFINITIONS]
    data = {"built": date.today().isoformat(), "source": xlsx, "groups": groups, "definitions": defs,
            "new": {"id": new["id"], "when": new["applies_when"], "notwhen": new["does_not_apply_when"]},
            "core": sum(len(g["codes"]) for g in groups), "anomalies": len(ANOMALY["codes"])}
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {out}: {data['core']} core codes, {data['anomalies']} anomaly codes, {len(groups)} groups")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
