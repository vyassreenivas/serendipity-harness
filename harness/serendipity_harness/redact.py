"""Write the coded interviews of a round with names and personal details replaced, for confidential review.

Usage: python -m serendipity_harness.redact WORK_DIR LISTS_DIR OUT_DIR CODEBOOK [EARLIER_KEY ...]

WORK_DIR is a coded round (cases.json, replies/, checked/<case_id>.segments.json).
LISTS_DIR holds one redaction list per interview, <case_id>.json:
  {"case_id": ..., "replace": [{"find": "Jane Doe", "with": "[FOUNDER]"}, ...]}
drafted by a model from the interview and its coding, and checked by a person.
Each "find" is replaced wherever it stands as a whole word, matching case, the
longest first; web addresses, emails and @handles are replaced as well. The same
replacements apply to the interview text and to every string of the coding
(story names, reasons, labels), so story names still match; the case id inside
segment ids is replaced too.

Interviews are renamed "Interview 01" and so on. An interview named in an
earlier round's key.json (EARLIER_KEY) keeps its number; new ones are numbered
after the highest earlier number, so a number means the same interview in every
round. Segments keep their numbers, so
every code still points to the same passage. The step checks that: each
interview has the same segments; the coding, checked against CODEBOOK (the
version the round was coded with), gives the same codes on the same segments
and the same anomalies; and no listed name is left. Words that match a name
only when case is ignored are printed for a person to look at.

Writes OUT_DIR/work (the redacted round), OUT_DIR/pages (the coded pages, each
marked confidential) and OUT_DIR/key.json (old name to new). Everything in
OUT_DIR still holds licensed interview text: keep it out of git and share it
only in confidence.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from . import coded_pages
from .coded_pages import check, use_round

WEB = [(re.compile(r"https?://\S+|www\.\S+"), "[WEBSITE]"),
       (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[EMAIL]"),
       (re.compile(r"(?<![\w.])@\w{2,}"), "[HANDLE]"),
       (re.compile(r"\b[\w-]+\.(?:com|io|co|net|org|ai|app|store|shop|me|so)\b", re.I), "[WEBSITE]")]
BANNER = ('<div style="background:#8a1c1c;color:#fff;padding:8px 14px;font:600 14px system-ui">Confidential, '
          'for review only. Licensed interview text with names and personal details replaced. Do not share.</div>')


def patterns(items: list[dict]) -> list[tuple[re.Pattern, str]]:
    items = sorted(items, key=lambda r: -len(r["find"]))
    return [(re.compile(r"(?<!\w)" + re.escape(r["find"]) + r"(?!\w)"), r["with"]) for r in items] + WEB


def apply(obj, pats):
    if isinstance(obj, str):
        for p, w in pats:
            obj = p.sub(w, obj)
        return obj
    if isinstance(obj, list):
        return [apply(x, pats) for x in obj]
    if isinstance(obj, dict):
        return {k: apply(v, pats) for k, v in obj.items()}
    return obj


def shape(coded: dict) -> tuple:
    """What the coding says, without its wording: codes with their segments, and anomalies."""
    order = {s["name"]: k for k, s in enumerate(coded["stories"])}
    ticks = sorted((d["code"], tuple(sorted((order.get(t["story"], -1), tuple(t["segments"])) for t in d["ticks"])))
                   for d in coded["decisions"])
    anos = sorted((a["code"], order.get(a["story"], -1), tuple(a["segments"])) for a in coded["anomalies"])
    return len(coded["stories"]), ticks, anos


def build(work: Path, lists: Path, out: Path, codebook: str, earlier: list[Path] = ()) -> None:
    (work_out := out / "work").mkdir(parents=True, exist_ok=True)
    (work_out / "replies").mkdir(exist_ok=True)
    (work_out / "checked").mkdir(exist_ok=True)
    (work_out / "round.json").write_text(json.dumps({"codebook": codebook}) + "\n", encoding="utf-8")
    cb = use_round(work_out)
    cases, key, problems, review = [], {}, [], []
    known = {o: n for k in earlier for n, o in json.loads(Path(k).read_text(encoding="utf-8")).items()}
    nxt = max((int(n.split("-")[1]) for n in known.values()), default=0)
    for case in json.loads((work / "cases.json").read_text(encoding="utf-8")):
        old = case["case_id"]
        if old not in known:
            nxt += 1
            known[old] = f"interview-{nxt:02d}"
        new = known[old]
        items = json.loads((lists / f"{old}.json").read_text(encoding="utf-8"))["replace"]
        pats = [(re.compile(re.escape(old)), new)] + patterns(items)  # segment ids carry the case id
        segs = json.loads((work / "checked" / f"{old}.segments.json").read_text(encoding="utf-8"))
        reply = json.loads((work / "replies" / f"{old}.json").read_text(encoding="utf-8"))
        r_segs, r_reply = apply(segs, pats), apply(reply, pats)
        if [s["role"] for s in segs] != [s["role"] for s in r_segs]:
            problems.append(f"{new}: segments changed")
        if shape(check(cb, old, segs, reply)) != shape(check(cb, new, r_segs, r_reply)):
            problems.append(f"{new}: coding differs after redaction")
        text = json.dumps([r_segs, r_reply], ensure_ascii=False)
        if old in text or old.rsplit("-", 1)[0] in text:
            problems.append(f"{new}: the original case id is still present")
        for r in items:
            if r["find"].lower() in r["with"].lower():  # a figure rounded in place, e.g. "$6K" -> "about $6K"
                continue
            if re.search(r"(?<!\w)" + re.escape(r["find"]) + r"(?!\w)", text):
                problems.append(f"{new}: '{r['with']}' name still present")
            elif len(r["find"]) > 3 and re.search(r"(?<!\w)" + re.escape(r["find"]) + r"(?!\w)", text, re.I):
                m = re.search(r"(?<!\w)" + re.escape(r["find"]) + r"(?!\w)", text, re.I)
                review.append(f"{new}: {r['with']} when case is ignored: ...{text[max(0, m.start() - 40):m.end() + 40]}...")
        (work_out / "checked" / f"{new}.segments.json").write_text(json.dumps(r_segs, ensure_ascii=False, indent=1),
                                                                   encoding="utf-8")
        (work_out / "replies" / f"{new}.json").write_text(json.dumps(r_reply, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
        cases.append(dict(case, case_id=new, case_no=new.split("-")[1], file=f"Interview {new.split('-')[1]}.txt"))
        key[new] = old
    cases.sort(key=lambda c: c["case_no"])
    (work_out / "cases.json").write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n", encoding="utf-8")
    for line in review:
        print("look at:", line)
    if problems:
        raise SystemExit("\n".join(problems))
    pages = out / "pages"
    if pages.exists():
        shutil.rmtree(pages)
    coded_pages.build(work_out, pages)
    for f in pages.glob("*.html"):
        f.write_text(re.sub(r"(<body[^>]*>)", r"\1" + BANNER, f.read_text(encoding="utf-8"), count=1), encoding="utf-8")
    print(f"{len(cases)} interviews redacted; same codes on the same segments; pages in {pages}")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], [Path(a) for a in sys.argv[5:]])
