"""Write the next codebook version from the previous one and a file of changes.

Usage: python -m serendipity_harness.next_version CHANGES_JSON

The changes file names the version it starts from and the one it makes, and
lists the codes to add or revise. Each entry gives the code's id, its wording
(label, definition, applies_when, does_not_apply_when), the anomaly theme it
comes from, why it changed, and its source: "literature" (papers that state it,
listed with their candidate codes and passages) or "inductive" (from the
interviews; no paper states it yet). An id from the drafted codes adopts that
drafted code; a new id adds a code. "merges" names drafted codes folded into
it, whose papers and passages it takes. A code marked "added_in" keeps the
numbers of the codes before it, so existing numbers never change.
"papers", when given, replaces the code's papers with those read in full that
state it, and keeps only their passages. "absorbs" lists the anomalies from the
last round that the code now covers, each with a comment; the file's
"open_anomalies" lists those no code covers yet, each with the reason. Both are
copied into the new version, so it shows which data moved where.
"dont_use_when", when given, rewrites the does_not_apply_when wording of codes
not otherwise listed: one line per case, each naming the code to use instead
or saying to leave the code off. An "extends" entry ({"was", "now"}) on a revised
code says in a few words how its meaning grew; it is for readers and is not
copied into the codebook.

Both files are kept in git, so any version can be remade from version 1.0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .runlog import ROOT, sha256

WORDING = ("label", "definition", "applies_when", "does_not_apply_when")


def build(changes_path: Path) -> Path:
    ch = json.loads(changes_path.read_text(encoding="utf-8"))
    src = ROOT / "harness" / "codebook" / f"codebook_v{ch['from']}.json"
    cb = json.loads(src.read_text(encoding="utf-8"))
    codes = {c["id"]: c for c in cb["codes"]}
    for c in codes.values():
        if c.get("core"):
            c.setdefault("source", "literature")
    for e in ch["codes"]:
        c = codes.get(e["id"])
        new = c is None or not c.get("core")
        if c is None:
            c = {"id": e["id"], "group": e["group"], "candidate_ids": [], "papers": [], "passage_ids": [],
                 "status": "accepted"}
            cb["codes"].append(c)
            codes[e["id"]] = c
        elif new:
            c["draft_wording"] = {k: c[k] for k in WORDING}
        for m in e.get("merges", []):
            for k in ("candidate_ids", "papers", "passage_ids"):
                c[k] = c[k] + [x for x in codes[m][k] if x not in c[k]]
            codes[m]["merged_into"] = e["id"]
        c.update({k: e[k] for k in WORDING})
        c.update(core=True, source=e["source"], change_note=e["why"])
        if new:
            c.update(added_in=ch["to"], from_theme=e.get("from_theme", ""))
        else:
            c["revised_in"] = c.get("revised_in", []) + [ch["to"]]
        if "papers" in e:
            c["papers"] = e["papers"]
            c["passage_ids"] = [p for p in c["passage_ids"] if p.split(":")[0] in e["papers"]]
        if e["source"] == "inductive":
            c.update(papers=[], candidate_ids=[], passage_ids=[])
        if e.get("absorbs"):
            c["absorbs"] = e["absorbs"]
    for i, text in ch.get("dont_use_when", {}).get("codes", {}).items():
        codes[i]["does_not_apply_when"] = text
        codes[i]["revised_in"] = codes[i].get("revised_in", []) + [ch["to"]]
    if "open_anomalies" in ch:
        cb["open_anomalies"] = ch["open_anomalies"]
    cb["version"] = ch["to"]
    cb["built_from"] = {"previous": f"codebook_v{ch['from']}.json", "previous_sha256": sha256(src),
                        "changes": str(changes_path.resolve().relative_to(ROOT)), "changes_sha256": sha256(changes_path)}
    out = src.with_name(f"codebook_v{ch['to']}.json")
    out.write_text(json.dumps(cb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(build(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
