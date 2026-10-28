"""Build a local coding page for one interview: codebook on the left, interview on the right.

Usage: python coding_page.py codebook_review.xlsx SEGMENTS.jsonl OUT.html [--case-no 001] [--load CODING.csv]

SEGMENTS.jsonl is one interview cut into segments by the harness (transcripts
stage). The page lets a coder code the whole interview story by story (each story a named
thread of segments), tick the core
and anomaly codes that apply to each, add notes, and export the coding as CSV
and JSON. Definitions of serendipity are not ticked: the page shows which ones
a story meets, worked out from the codes ticked, and exports them. Selecting words in the interview before ticking a code ties the
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

from export import LEVELS
from levels import NEW, level1
from workbook import load_draft, state_from_workbook

TEMPLATE = Path(__file__).with_name("coding_page_template.html")
CODEBOOK_NAME = "codebook version 1.0"


def evidence(text: str) -> dict:
    """'trigger-24 @s05: "words" | ...' -> {code: [{seg, text}]}"""
    out = {}
    for code, seg, words in re.findall(r'([\w-]+) @s(\d+): "(.*?)"(?= \| |$)', text):
        out.setdefault(code, []).append({"seg": int(seg), "text": words})
    return out


FIXED = {"case_no", "case_id", "coder", "codebook", "story", "story_name", "summary", "episode", "segments", "what_was_unexpected",
         "anomaly_codes", "anomaly_notes", "notes", "evidence"}


def prefill(path: str, known: set) -> dict:
    """A coding CSV (as the page exports it) turned back into the page's state.
    Codes that are not in this codebook (for example from an older version) are left out."""
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    code_cols = [c for c in (rows[0] if rows else {}) if c not in FIXED and not c.startswith(("def_", "riv_", "typ_"))] + ["anomaly_codes"]
    eps = []
    for r in rows:
        story = r.get("story") or r.get("episode")  # older files used episodes
        if not story or story == "0":
            continue
        codes = [c.strip() for col in code_cols for c in (r.get(col) or "").split(";") if c.strip() in known]
        notes = dict(re.findall(r"(ANO-[A-Z]{3}): (.*?)(?= \| ANO-|$)", r.get("anomaly_notes") or ""))
        eps.append({"id": f"e{story}", "name": r.get("story_name", ""), "segments": [int(x) for x in re.findall(r"\d+", r.get("segments") or "")],
                    "codes": codes, "unexpected": r.get("summary") or r.get("what_was_unexpected", ""), "notes": r.get("notes", ""),
                    "anomaly_notes": notes, "evidence": evidence(r.get("evidence") or "")})
    none = any((r.get("story") or r.get("episode")) == "0" for r in rows)
    import hashlib
    version = hashlib.sha256(Path(path).read_bytes()).hexdigest()[:10]  # a changed file opens fresh, not an old saved copy
    return {"coder": rows[0]["coder"] if rows else "", "version": version,
            "state": {"episodes": eps, "active": eps[0]["id"] if eps else None, "none": none}}


def build(xlsx: str, segments_path: str, out: str, case_no: str, load: str | None = None) -> None:
    state = state_from_workbook(xlsx)
    draft = load_draft()
    def code(cid, pick=None):
        st = state[cid]
        return {"id": cid, "label": st["Label"], "when": st["Code it when"], "example": st["Example (made up)"],
                "notwhen": st["Not when"], "description": st["Description"], **({"pick": pick} if pick else {})}

    groups = []
    for gi, g in enumerate(level1(state, draft), 1):
        p = g["pick_one"]
        codes = ([code(c, p["name"]) for c in p["codes"]] if p else []) + [code(c) for c in g["codes"]]
        if g["anomaly"]:
            m = g["anomaly"]
            codes.append({"id": m["id"], "label": "None of these fits", "when": m["applies_when"], "example": "",
                          "notwhen": m["does_not_apply_when"], "description": "", "anomaly": True})
        groups.append({"n": gi, "name": g["group"], "title": g["name"], "asks": g["asks"],
                       "pick_note": f"{p['name']}: {p['asks']} Pick one." if p else "", "codes": codes})
    groups.append({"n": len(groups) + 1, "name": "something else", "title": "Something else",
                   "asks": "Is there something relevant that no group asks about?", "pick_note": "",
                   "codes": [{"id": NEW["id"], "label": "Something no group asks about", "when": NEW["applies_when"],
                              "example": "", "notwhen": NEW["does_not_apply_when"], "description": "", "anomaly": True}]})
    labels = {c["id"]: c["label"] for g in groups for c in g["codes"]}
    rules = [{"id": r["id"], "kind": r["kind"], "name": r["name"], "in_short": r["in_short"],
              **{k: [{"id": c, "label": labels[c]} for c in r.get(k, [])] for k in ("all", "any", "none")}}
             for r in LEVELS["level2"] if r["kind"] != "judgment"]

    segs = [json.loads(line) for line in open(segments_path, encoding="utf-8")]
    case_id = segs[0]["segment_id"].split(":")[0]
    header = next((s["text"] for s in segs if s["role"] == "header"), "")
    title = next((l.split(":", 1)[1].strip() for l in header.splitlines() if l.startswith("INTERVIEW:")), case_id)
    data = {"case_id": case_id, "case_no": case_no, "title": title, "built": date.today().isoformat(),
            "codebook": CODEBOOK_NAME, "groups": groups, "rules": rules,
            "segments": [{"n": k, "role": s["role"], "text": s["text"]} for k, s in enumerate(segs, 1)],
            "prefill": prefill(load, set(labels)) if load else None}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", payload)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(html, encoding="utf-8")
    print(f"wrote {out}: {case_id}, {len(segs)} segments, "
          f"{sum(len(g['codes']) for g in groups)} codes in {len(groups)} groups, {len(rules)} rules")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("xlsx"); a.add_argument("segments"); a.add_argument("out")
    a.add_argument("--case-no", default="")
    a.add_argument("--load", default=None, help="a coding CSV to show when the page opens")
    x = a.parse_args()
    build(x.xlsx, x.segments, x.out, x.case_no, x.load)
