"""Build a local coding page for one interview: codebook on the left, interview on the right.

Usage: python coding_page.py codebook_review.xlsx SEGMENTS.jsonl OUT.html [--case-no 001] [--load CODING.csv]

SEGMENTS.jsonl is one interview cut into segments by the harness (transcripts
stage). The page lets a coder mark episodes (groups of segments), tick the core
and anomaly codes that apply to each, add notes, and export the coding as CSV
and JSON. Definitions of serendipity are not ticked: the page shows which ones
an episode meets, worked out from the codes ticked, and exports them. Selecting words in the interview before ticking a code ties the
code to those words (its evidence). Work is kept in the browser as it goes; Export writes the files.
With --load, the page opens showing a coding exported earlier (for example
the model's), under that coder's name.

The page holds the full interview text. Write it to harness_v2/outputs/,
which git ignores, and never publish it.
"""
from __future__ import annotations

import argparse
import csv
import re
import json
from datetime import date
from pathlib import Path

from export import DEFINITIONS, GROUPS, MISFIT
from workbook import load_draft, state_from_workbook

TEMPLATE = Path(__file__).with_name("coding_page_template.html")


def evidence(text: str) -> dict:
    """'trigger-24 @s05: "words" | ...' -> {code: [{seg, text}]}"""
    out = {}
    for code, seg, words in re.findall(r'([\w-]+) @s(\d+): "(.*?)"(?= \| |$)', text):
        out.setdefault(code, []).append({"seg": int(seg), "text": words})
    return out


def prefill(path: str) -> dict:
    """A coding CSV (as the page exports it) turned back into the page's state."""
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    eps = []
    for r in rows:
        if not r.get("episode") or r["episode"] == "0":
            continue
        codes = [c.strip() for col in ("definition", "type", "rival", "trigger", "background", "mechanism", "role",
                                       "outcome", "condition", "account", "anomaly_codes")
                 for c in (r.get(col) or "").split(";") if c.strip()]
        notes = dict(re.findall(r"(ANO-[A-Z]{3}): (.*?)(?= \| ANO-|$)", r.get("anomaly_notes") or ""))
        eps.append({"id": f"e{r['episode']}", "segments": [int(x) for x in re.findall(r"\d+", r.get("segments") or "")],
                    "codes": codes, "unexpected": r.get("what_was_unexpected", ""), "notes": r.get("notes", ""),
                    "anomaly_notes": notes, "evidence": evidence(r.get("evidence") or "")})
    none = any(r.get("episode") == "0" for r in rows)
    import hashlib
    version = hashlib.sha256(Path(path).read_bytes()).hexdigest()[:10]  # a changed file opens fresh, not an old saved copy
    return {"coder": rows[0]["coder"] if rows else "", "version": version,
            "state": {"episodes": eps, "active": eps[0]["id"] if eps else None, "none": none}}


def build(xlsx: str, segments_path: str, out: str, case_no: str, load: str | None = None) -> None:
    state = state_from_workbook(xlsx)
    draft = load_draft()
    anomaly_by_group = {m.get("overflows_from") or "new": m for m in MISFIT["codes"]}
    groups = []
    for gi, (name, _sq, asks) in enumerate(GROUPS, 1):
        if name == "anomaly":
            continue
        codes = []
        for cid in sorted((i for i in draft if draft[i]["group"] == name), key=lambda i: int(i.split("-")[1])):
            s = state[cid]
            if s["Status"] != "core":
                continue
            codes.append({"id": cid, "label": s["Label"], "when": s["Code it when"], "example": s["Example (made up)"],
                          "notwhen": s["Not when"], "description": s["Description"]})
        m = anomaly_by_group.get(name)
        if m:
            codes.append({"id": m["id"], "label": "None of these fits", "when": m["applies_when"], "example": "",
                          "notwhen": m["does_not_apply_when"], "description": "", "anomaly": True})
        groups.append({"n": gi, "name": name, "asks": asks, "codes": codes})
    m = anomaly_by_group.get("new") or next(x for x in MISFIT["codes"] if x["id"] == "ANO-NEW")
    groups.append({"n": len(groups) + 1, "name": "something else", "asks": "Is there something relevant that no group asks about?",
                   "codes": [{"id": m["id"], "label": "Something no group asks about", "when": m["applies_when"],
                              "example": "", "notwhen": m["does_not_apply_when"], "description": "", "anomaly": True}]})

    segs = [json.loads(line) for line in open(segments_path, encoding="utf-8")]
    case_id = segs[0]["segment_id"].split(":")[0]
    header = next((s["text"] for s in segs if s["role"] == "header"), "")
    title = next((l.split(":", 1)[1].strip() for l in header.splitlines() if l.startswith("INTERVIEW:")), case_id)
    labels = {c["id"]: c["label"] for g in groups for c in g["codes"]}
    definitions = [{"id": d["id"], "name": d["name"], "in_short": d["in_short"],
                    "needs": [{"id": cid, "part": part, "label": labels[cid]} for cid, part in d["needs"]]} for d in DEFINITIONS]
    data = {"case_id": case_id, "case_no": case_no, "title": title, "built": date.today().isoformat(),
            "codebook": f"{Path(xlsx).name} (draft, not frozen)", "groups": groups, "definitions": definitions,
            "segments": [{"n": k, "role": s["role"], "text": s["text"]} for k, s in enumerate(segs, 1)],
            "prefill": prefill(load) if load else None}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", payload)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(html, encoding="utf-8")
    print(f"wrote {out}: {case_id}, {len(segs)} segments, "
          f"{sum(len(g['codes']) for g in groups)} codes in {len(groups)} groups")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("xlsx"); a.add_argument("segments"); a.add_argument("out")
    a.add_argument("--case-no", default="")
    a.add_argument("--load", default=None, help="a coding CSV to show when the page opens")
    x = a.parse_args()
    build(x.xlsx, x.segments, x.out, x.case_no, x.load)
