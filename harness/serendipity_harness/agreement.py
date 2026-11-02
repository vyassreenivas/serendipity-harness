"""Compare two codings of the same interviews, code by code.

Usage: python -m serendipity_harness.agreement WORK_A WORK_B OUT_CSV [--only WORK [--new]]

WORK_A and WORK_B are round folders (cases.json, replies/, checked/); each is
checked with its own codebook (round.json, else project.toml's). For every
level-1 code in both codebooks, each shared interview counts as "yes" if the
code is ticked anywhere in it. The CSV gives, per code, how often the two
codings agree, Cohen's kappa (agreement beyond chance), Gwet's AC1 (the same,
but not pulled to zero when a code is in nearly every interview or almost none,
where kappa misleads), and whether the code's
wording differs between the two codebooks, since a changed code can explain a
change in coding. Anomalies are compared per interview by count. --only limits the comparison to the
interviews of one round folder; with --new, to those drawn new in that round, so
each round's interviews get their own score.

Two codings by the same model show how stable its coding is (intra-coder
reliability); a model's and a person's coding show how far they agree.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .coded_pages import cb_path, check, numbering, use_round
from .runlog import HARNESS

WORDING = ("label", "definition", "applies_when", "does_not_apply_when")


def coding(work: Path) -> tuple[dict, dict, dict, dict]:
    cb = use_round(work)
    raw = {c["id"]: c for c in json.loads((HARNESS / cb_path()).read_text(encoding="utf-8"))["codes"]}
    num, _ = numbering(cb)
    out = {}
    for case in json.loads((work / "cases.json").read_text(encoding="utf-8")):
        cid = case["case_id"]
        segs = json.loads((work / "checked" / f"{cid}.segments.json").read_text(encoding="utf-8"))
        reply = json.loads((work / "replies" / f"{cid}.json").read_text(encoding="utf-8"))
        k = check(cb, cid, segs, reply)
        out[cid] = ({d["code"] for d in k["decisions"] if d["ticks"]}, len(k["anomalies"]))
    return cb, raw, num, out


def kappa(a: int, b: int, c: int, d: int) -> float | None:
    n = a + b + c + d
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n / n
    return None if pe == 1 else (po - pe) / (1 - pe)


def ac1(a: int, b: int, c: int, d: int) -> float:
    n = a + b + c + d
    po = (a + d) / n
    q = ((a + b) + (a + c)) / (2 * n)
    pe = 2 * q * (1 - q)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def compare(wa: Path, wb: Path, only: set | None = None) -> list[dict]:
    cba, rawa, num, A = coding(wa)
    cbb, rawb, _, B = coding(wb)
    cases = [c for c in A if c in B and (only is None or c in only)]
    codes = [c for c in cba["labels"] if c in cbb["labels"] and c in num and not num[c].endswith(".A")
             and any(c in g["codes"] for g in cba["groups"]) and any(c in g["codes"] for g in cbb["groups"])]
    rows = []
    for c in codes:
        both = sum(c in A[x][0] and c in B[x][0] for x in cases)
        a_only = sum(c in A[x][0] and c not in B[x][0] for x in cases)
        b_only = sum(c not in A[x][0] and c in B[x][0] for x in cases)
        neither = len(cases) - both - a_only - b_only
        k = kappa(both, a_only, b_only, neither)
        rows.append({"no": num[c], "code": c, "label": cba["labels"][c], "both": both, "only_a": a_only,
                     "only_b": b_only, "neither": neither, "agree": round((both + neither) / len(cases), 2),
                     "kappa": "" if k is None else round(k, 2), "ac1": round(ac1(both, a_only, b_only, neither), 2),
                     "wording_changed": any(rawa.get(c, {}).get(w) != rawb.get(c, {}).get(w) for w in WORDING)})
    rows.append({"no": "", "code": "anomalies", "label": "anomaly count per interview",
                 "both": sum(A[x][1] for x in cases), "only_a": "", "only_b": sum(B[x][1] for x in cases),
                 "neither": "", "agree": round(sum(A[x][1] == B[x][1] for x in cases) / len(cases), 2),
                 "kappa": "", "ac1": "", "wording_changed": ""})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("work_a", type=Path)
    ap.add_argument("work_b", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--only", type=Path)
    ap.add_argument("--new", action="store_true")
    a = ap.parse_args()
    only = None if a.only is None else {c["case_id"] for c in json.loads((a.only / "cases.json").read_text(encoding="utf-8"))
                                        if not a.new or c.get("in_round") == "new"}
    rows = compare(a.work_a, a.work_b, only)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r["no"], r["label"][:40], r["both"], r["only_a"], r["only_b"], r["neither"], r["agree"], r["kappa"],
              "changed" if r["wording_changed"] else "")


if __name__ == "__main__":
    main()
