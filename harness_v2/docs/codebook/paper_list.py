"""Export the papers behind the codebook, and the codes each one supports, as JSON for paper_list.js.

Usage: python paper_list.py codebook_review.xlsx paper_list.json [CODEBOOK_JSON]
       node paper_list.js paper_list.json paper_list.docx

One row per work the model read for candidate codes (versions of one work are
merged). For each: its reference and the level-1 codes and level-2 items it
supports (each level-2 item with its rule over level-1 codes), numbered as in the codebook document (2.3 is the third code of group
2). A link counts only where a sentence chosen by reading states the code;
"leans on it" marks a sentence that comes close. Works that support no code in
the codebook are listed last. Holds references and code labels only.
With a later codebook version (CODEBOOK_JSON), its added codes are linked to
their papers through sentences picked by fixed code, marked "not yet read" until
chosen by reading.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

from export import ADDED, H, LEVELS, META, cite
from levels import level1, numbers, rule_equation, rule_evidence
from version import apply
from workbook import evidence_for, load_draft, state_from_workbook

WHY = json.loads(Path(__file__).with_name("paper_why.json").read_text(encoding="utf-8"))["why"]
CORE = json.loads((H / "codebook" / "core_papers.json").read_text(encoding="utf-8"))["papers"]
KINDS = {"definition": "D", "rival": "R", "type": "T", "judgment": "J"}


def from_file(pid: str) -> dict:
    """A work with no looked-up metadata: author, year and title from its file name."""
    for run in ("20261012-124904", ADDED["run"]):
        for e in json.loads((H / "runs" / run / "inventory.json").read_text(encoding="utf-8")):
            if e["paper_id"] == pid:
                author, year, title = Path(e["file"]).stem.split(" - ", 2)
                return {"short": f"{author.replace(' et al', ' et al.')} ({year})", "title": title, "venue": "", "url": ""}
    raise KeyError(pid)


def reference(pid: str) -> dict:
    c, m = (cite(pid), META[pid]) if pid in META else (from_file(pid), {})
    vol = "".join([f", {m['volume']}" if m.get("volume") else "", f"({m['issue']})" if m.get("issue") else "",
                   f", {m['page']}" if m.get("page") else ""])
    return {"short": c["short"], "text": f"{c['title']}." + (f" {c['venue']}{vol}." if c["venue"] else ""), "url": c["url"]}


def build(xlsx: str, out: str, version_file: str = "") -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    version = apply(state, draft, version_file) if version_file else "1.0"
    read = sorted(p.stem for run in ("20261012-124904", ADDED["run"]) for p in (H / "runs" / run / "candidates").glob("*.json"))
    works = {}
    for pid in read:
        r = reference(pid)
        works.setdefault(r["short"] + r["url"], dict(r, ids=[], l1=[], l2=[]))["ids"].append(pid)
    key = lambda e: e["short"] + e["url"]

    sq_of = {}  # level-1 group number -> sub-question
    for gi, g in enumerate(level1(state, draft), 1):
        sq_of[str(gi)] = g["sq"]
        ids = (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]
        for k, c in enumerate(ids, 1):
            for e in evidence_for(draft[c]):
                if (e["chosen"] or draft[c].get("unread")) and not e.get("none") and key(e) in works:
                    unread = " (added in " + draft[c]["added_in"] + "; sentence not yet read)" if not e["chosen"] else ""
                    works[key(e)]["l1"].append({"no": f"{gi}.{k}", "label": state[c]["Label"] + unread,
                                                "leans": bool(e.get("close"))})
    counters, num = {}, numbers(state, draft)
    label = {c: state[c]["Label"] for c in draft}
    for r in LEVELS["level2"]:
        letter = KINDS[r["kind"]]
        counters[letter] = counters.get(letter, 0) + 1
        for e in rule_evidence(r, draft):
            if key(e) in works:
                item = {"no": f"{letter}{counters[letter]}", "label": r["name"], "leans": bool(e.get("close")),
                        "rule": rule_equation(r, label, num) if r["kind"] != "judgment" else "Decided by the researchers"}
                if item["no"] not in [x["no"] for x in works[key(e)]["l2"]]:
                    works[key(e)]["l2"].append(item)

    for w in works.values():  # chapters of one book are cited as the book
        m = META.get(w["ids"][0], {})
        if len(w["ids"]) > 1 and m.get("book"):
            w["text"] = f"{m['book']}." + (f" {m['publisher']}." if m.get("publisher") else "")
    rows = sorted(works.values(), key=lambda w: w["short"].lower())
    used = [w for w in rows if w["l1"] or w["l2"]]
    data = {"version": version, "built": date.today().isoformat(), "read": len(read), "works": len(rows),
            "used": [dict({k: v for k, v in w.items() if k != "ids"}, key=w["ids"][0], why=WHY[w["ids"][0]]) for w in used],
            "unused": [dict({k: v for k, v in w.items() if k not in ("ids", "l1", "l2")}, key=w["ids"][0], why=WHY[w["ids"][0]]) for w in rows if not (w["l1"] or w["l2"])],
            "links": sum(len(w["l1"]) for w in used), "leans": sum(x["leans"] for w in used for x in w["l1"])}
    data["core"] = core(data["used"], sq_of)
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {out}: {data['read']} papers read ({data['works']} works); {len(used)} support a code, "
          f"{len(data['unused'])} support none; {data['links']} level-1 links, {data['leans']} lean on it")


def sub_questions(w: dict, sq_of: dict, needed: set) -> list[str]:
    """A work's main sub-questions: those where it states two or more codes. A level-1 code counts
    under its group's sub-question; definitions, rivals and types count under SQ1 (what counts);
    judgments are left out. Added to these: the sub-questions of the codes it is in the core for
    (needed), so the list says why the work is there."""
    def sq(no):
        return sq_of[no.split(".")[0]] if "." in no else (None if no.startswith("J") else "SQ1")
    count = {}
    for x in w["l1"] + w["l2"]:
        if not x["leans"] and sq(x["no"]):
            count[sq(x["no"])] = count.get(sq(x["no"]), 0) + 1
    main = {q for q, n in count.items() if n >= 2}
    return sorted(main | {sq(i) for i in needed if sq(i)})


def core(used: list[dict], sq_of: dict) -> dict:
    """The core papers (core_papers.json) with their sub-questions, and a check that together they
    state every code, counting only sentences that state it (not those that lean on it)."""
    by_key = {w["key"]: w for w in used}
    states = lambda w: {x["no"] for x in w["l1"] + w["l2"] if not x["leans"]}
    every = set().union(*(states(w) for w in used))
    avail = {i: sum(i in states(w) for w in used) for i in every}
    picked = [by_key[c["key"]] for c in CORE]
    needed = lambda w: {i for i in states(w) if sum(i in states(o) for o in picked) <= min(2, avail[i])}
    rows = [dict(w, why=c["why"], sq=sub_questions(w, sq_of, needed(w))) for c, w in zip(CORE, picked)]
    for r in rows:  # the line must name exactly the sub-questions the table lists
        named = sorted(set(re.findall(r"\((SQ\d)\)", r["why"])))
        if named != r["sq"]:
            print(f"  {r['short']}: line names {named}, table lists {r['sq']}")
    count = {i: sum(i in states(w) for w in rows) for i in every}
    missing = sorted(i for i, n in count.items() if n == 0)
    single = sorted(i for i, n in count.items() if n == 1 and sum(i in states(w) for w in used) > 1)
    print(f"core: {len(rows)} papers state {len(every) - len(missing)} of {len(every)} codes"
          + (f"; MISSING {missing}" if missing else "") + (f"; only one core source though more exist: {single}" if single else ""))
    full = {r["sq"]: r["text"] for r in json.loads(Path(__file__).with_name("questions.json").read_text(encoding="utf-8"))["rows"]}
    sqs = [{"sq": q.replace("SQ", ""), "text": full[q.replace("SQ", "")]} for q in sorted(set(sq_of.values()))]
    question = json.loads(Path(__file__).with_name("questions.json").read_text(encoding="utf-8"))["question"]
    return {"papers": rows, "codes": len(every), "missing": missing, "single": single, "question": question, "sub_questions": sqs}


if __name__ == "__main__":
    build(*sys.argv[1:4])
