"""The anomaly log: every anomaly theme across all coding rounds, and what became of it.

Usage:
  python -m serendipity_harness.anomaly_log add WORK_DIR --round N [--coders model vyas ...]
  python -m serendipity_harness.anomaly_log search THEME_ID --where SOURCE --query TEXT --hits N [--kept PAPER ...] [--note TEXT]
  python -m serendipity_harness.anomaly_log set THEME_ID STATUS [--code 2.7 --version 2.0] [--papers PAPER ...] [--note TEXT]
  python -m serendipity_harness.anomaly_log show

The codebook starts small and grows. After each round, the researchers group the
round's anomalies, from every coder, into themes (WORK_DIR/anomaly_themes.json, the
same file the anomalies page reads). Each coder's anomalies are numbered A01, A02,
... in interview order; a theme lists them as "vyas:A03", and a bare "A03" means the
model's. The model's checked coding is in WORK_DIR/checked/, a researcher's in
WORK_DIR/coders/<name>/checked/ (written by the compare step). `add` merges the
round into the log: a theme whose id is already in the log gains the new anomalies;
a new id starts a new open theme. Re-adding the same round and coder replaces its
earlier entries, so `add` can be rerun. `set` records a decision: a theme is "open", "adopted" (it became a code in
a codebook version) or "dropped" (with a reason). Open themes carry forward to the
next round; those still open at the end are reported as findings.

Before a recurring theme becomes a code, the researchers look for the papers that
state it. `search` records each search: where (for example a catalogue of journal
abstracts, or the full texts held), the query, how many hits, and the papers read
in full and kept. Kept papers join the theme's papers. A theme no kept paper states
can still be adopted, as an inductive code from the data. A model may suggest
queries or candidates, but only papers the researchers have read are kept.

The log is harness/codebook/anomaly_log.json (path in project.toml, [coding]
anomaly_log), with a one-row-per-theme copy in anomaly_log.csv. It names
interviews by id and segment numbers only, never their words, so it can be kept
in git with the codebook.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import tomllib
from datetime import date
from pathlib import Path

from .runlog import HARNESS, ROOT, sha256

STATUSES = ("open", "adopted", "dropped")


def log_path() -> Path:
    cfg = tomllib.loads((HARNESS / "project.toml").read_text(encoding="utf-8"))
    return ROOT / cfg["coding"]["anomaly_log"]


def load() -> dict:
    p = log_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"about": "Anomaly themes across coding rounds. Written by serendipity_harness.anomaly_log; "
                     "decisions are made with its `set` command, not by editing this file.",
            "rounds": [], "themes": []}


def save(log: dict) -> None:
    p = log_path()
    p.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cols = ["theme_id", "name", "group", "status", "code", "version", "first_round", "interviews",
            "anomalies", "by_round", "searches", "papers", "what", "note"]
    with open(p.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for t in log["themes"]:
            by_round = {}
            for a in t["anomalies"]:
                by_round.setdefault(f'{a["round"]} ({a["coder"]})', set()).add(a["case_id"])
            w.writerow([t["id"], t["name"], t["group"], t["status"], t.get("code", ""), t.get("version", ""),
                        t["first_round"], len({a["case_id"] for a in t["anomalies"]}), len(t["anomalies"]),
                        "; ".join(f"round {k}: {len(v)}" for k, v in by_round.items()),
                        len(t.get("searches", [])), "; ".join(t["papers"]), t["what"], t.get("note", "")])


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def checked_dir(work: Path, coder: str) -> Path:
    return work / "checked" if coder == "model" else work / "coders" / coder / "checked"


def coders_in(work: Path) -> list[str]:
    """The coders with checked coding in a round's folder: the model first, then the researchers."""
    out = ["model"] if any(p for p in (work / "checked").glob("*.json") if not p.name.endswith(".segments.json")) else []
    return out + sorted(p.parent.name for p in (work / "coders").glob("*/checked") if any(p.glob("*.json")))


def numbered(work: Path, coder: str) -> dict:
    """One coder's checked anomalies in a round, numbered A01, A02, ... in interview order, as on the anomalies page."""
    out, k = {}, 0
    for case in json.loads((work / "cases.json").read_text(encoding="utf-8")):
        checked = checked_dir(work, coder) / f"{case['case_id']}.json"
        if not checked.exists():
            continue
        for a in json.loads(checked.read_text(encoding="utf-8"))["anomalies"]:
            k += 1
            out[f"{coder}:A{k:02d}"] = {"case_id": case["case_id"], "story": a["story"], "code": a["code"],
                                        "segments": a["segments"], "coder": coder, "no": f"A{k:02d}"}
    return out


def ref(i: str) -> str:
    return i if ":" in i else f"model:{i}"


def add(work: Path, round_no: int, coders: list[str], codebook: str) -> list[str]:
    """Merge one round's themed anomalies, for the coders named, into the log. Returns the problems found."""
    anos = {k: v for c in coders for k, v in numbered(work, c).items()}
    themes_file = work / "anomaly_themes.json"
    themes = json.loads(themes_file.read_text(encoding="utf-8"))["themes"]
    problems, seen = [], {}
    for t in themes:
        t.setdefault("id", slug(t["name"]))
        for i in map(ref, t["anomalies"]):
            if i.split(":")[0] not in coders:
                continue
            if i not in anos:
                problems.append(f'{t["id"]}: {i} is not an anomaly in this round')
            elif i in seen:
                problems.append(f'{i} is in two themes: {seen[i]} and {t["id"]}')
            seen.setdefault(i, t["id"])
    problems += [f"{i} is in no theme" for i in anos if i not in seen]
    if problems:
        return problems

    log = load()
    log["rounds"] = [r for r in log["rounds"] if not (r["round"] == round_no and r["coder"] in coders)]
    for c in coders:
        mine = [a for a in anos.values() if a["coder"] == c]
        log["rounds"].append({"round": round_no, "coder": c, "codebook": codebook, "added": date.today().isoformat(),
                              "work": str(work.resolve().relative_to(ROOT)) if work.resolve().is_relative_to(ROOT) else str(work),
                              "interviews": len({a["case_id"] for a in mine}), "anomalies": len(mine),
                              "themes_sha256": sha256(themes_file)})
    by_id = {t["id"]: t for t in log["themes"]}
    for t in log["themes"]:
        t["anomalies"] = [a for a in t["anomalies"] if not (a["round"] == round_no and a["coder"] in coders)]
    for t in themes:
        mine = [anos[i] for i in map(ref, t["anomalies"]) if i in anos]
        entry = by_id.get(t["id"])
        if entry is None:
            if not mine:
                continue
            entry = {"id": t["id"], "name": t["name"], "group": t["group"], "what": t["what"], "status": "open",
                     "first_round": round_no, "papers": [], "anomalies": [], "history": []}
            log["themes"].append(entry)
            by_id[t["id"]] = entry
        entry["anomalies"] += [dict(a, round=round_no) for a in mine]
    log["themes"] = [t for t in log["themes"] if t["anomalies"] or t["status"] != "open"]
    save(log)
    return []


def set_status(theme_id: str, status: str, code: str = "", version: str = "", note: str = "",
               papers: list[str] | None = None) -> None:
    if status not in STATUSES:
        raise SystemExit(f"status must be one of {', '.join(STATUSES)}")
    if status == "adopted" and not (code and version):
        raise SystemExit("an adopted theme needs --code and --version")
    if status == "dropped" and not note:
        raise SystemExit("a dropped theme needs --note with the reason")
    log = load()
    t = next((t for t in log["themes"] if t["id"] == theme_id), None)
    if t is None:
        raise SystemExit(f"no theme {theme_id}")
    t.update(status=status, code=code, version=version, note=note)
    if papers is not None:
        t["papers"] = papers
    t["history"].append({"date": date.today().isoformat(), "status": status, "code": code, "version": version, "note": note})
    save(log)


def search(theme_id: str, where: str, query: str, hits: int, kept: list[str], note: str = "") -> None:
    log = load()
    t = next((t for t in log["themes"] if t["id"] == theme_id), None)
    if t is None:
        raise SystemExit(f"no theme {theme_id}")
    t.setdefault("searches", []).append({"date": date.today().isoformat(), "where": where, "query": query,
                                         "hits": hits, "kept": kept, "note": note})
    t["papers"] += [p for p in kept if p not in t["papers"]]
    save(log)


def show() -> None:
    log = load()
    for r in log["rounds"]:
        print(f'round {r["round"]} ({r["coder"]}, codebook {r["codebook"]}): {r["anomalies"]} anomalies '
              f'in {r["interviews"]} interviews')
    for t in sorted(log["themes"], key=lambda t: (STATUSES.index(t["status"]), -len({a["case_id"] for a in t["anomalies"]}))):
        n = len({a["case_id"] for a in t["anomalies"]})
        extra = f' -> {t["code"]} in v{t["version"]}' if t["status"] == "adopted" else ""
        print(f'  {t["status"]:8} {n:3} interviews  {t["group"]:24} {t["name"]}{extra}')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("work", type=Path)
    a.add_argument("--round", type=int, required=True)
    a.add_argument("--coders", nargs="*", help="default: every coder with checked coding in WORK_DIR")
    s = sub.add_parser("set")
    s.add_argument("theme_id")
    s.add_argument("status")
    s.add_argument("--code", default="")
    s.add_argument("--version", default="")
    s.add_argument("--note", default="")
    s.add_argument("--papers", nargs="*")
    q = sub.add_parser("search")
    q.add_argument("theme_id")
    q.add_argument("--where", required=True)
    q.add_argument("--query", required=True)
    q.add_argument("--hits", type=int, required=True)
    q.add_argument("--kept", nargs="*", default=[])
    q.add_argument("--note", default="")
    sub.add_parser("show")
    args = ap.parse_args()
    if args.cmd == "add":
        cfg = tomllib.loads((HARNESS / "project.toml").read_text(encoding="utf-8"))
        codebook = json.loads((ROOT / cfg["coding"]["codebook"]).read_text(encoding="utf-8"))["version"]
        problems = add(args.work, args.round, args.coders or coders_in(args.work), codebook)
        for p in problems:
            print(p)
        if problems:
            raise SystemExit("nothing added; fix the themes file and run again")
    elif args.cmd == "search":
        search(args.theme_id, args.where, args.query, args.hits, args.kept, args.note)
    elif args.cmd == "set":
        set_status(args.theme_id, args.status, args.code, args.version, args.note, args.papers)
    show()


if __name__ == "__main__":
    main()
