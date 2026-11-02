"""Bring a later codebook version into the documents built from the review workbook.

The workbook holds version 1.0 as the researchers reviewed it. A later version
(harness/codebook/codebook_v<n>.json, written by next_version) adds and revises
codes. `apply` lays those codes over the workbook's state and the draft, so the
paper list and the code sources show the version named. A code added later
keeps its place after the codes before it, so numbers do not change.

Sentences for codes added after 1.0 are picked by the fixed code until they are
chosen by reading; `unread` marks them, and the documents say so.
"""
import json
from pathlib import Path


def apply(state: dict, draft: dict, path: str | Path) -> str:
    cb = json.loads(Path(path).read_text(encoding="utf-8"))
    for c in cb["codes"]:
        if not c.get("core") or not (c.get("added_in") or c.get("revised_in")):
            continue
        d = draft.setdefault(c["id"], {"id": c["id"], "group": c["group"], "papers": [], "passage_ids": [],
                                       **{k: c[k] for k in ("label", "definition", "applies_when", "does_not_apply_when")}})
        if c.get("added_in"):
            d.update(papers=c["papers"], passage_ids=c["passage_ids"], added_in=c["added_in"],
                     source=c.get("source", "literature"), unread=True)
        state[c["id"]] = dict(state.get(c["id"], {}), Status="core", Label=c["label"], Description=c["definition"],
                              **{"Code it when": c["applies_when"], "Not when": c["does_not_apply_when"]})
    return cb["version"]
