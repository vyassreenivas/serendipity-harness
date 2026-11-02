"""Step 6: compare the coders of one round, story by story.

Usage: python -m serendipity_harness.compare WORK_DIR

WORK_DIR is one round's folder. It holds cases.json, checked/<case_id>.segments.json
(the numbered segments every coder saw) and the codings:

  replies/<case_id>.json          the model's replies (checked as on the coded pages)
  coders/<name>/*.csv or *.json   what each researcher exported from the coding page

Each researcher's export is turned into the same form as the model's checked coding
(stories, code decisions with ticks, anomalies) and saved as
coders/<name>/checked/<case_id>.json, so all coders go through the same checks, the
same level-2 rules and the same anomaly log. A tick needs a cited segment: a code
ticked on the page with no highlighted words takes its story's segments, and this
is listed as a problem for the coder to fix.

Story names differ between coders, so stories are matched by the segments they
cite. The report, in WORK_DIR/comparison/, gives for every pair of coders:
  - code agreement per interview (was the code used anywhere?), by code and by group,
    with Cohen's kappa;
  - how closely the cited segments overlap where both used a code;
  - level-2 agreement on matched stories, and per interview;
  - near misses: where one coder used an anomaly code and the other ticked a code of
    the same group on the same segments;
  - how often each code was used, and the codes no coder used.
Every input file is listed with its fingerprint in comparison/manifest.json.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from .anomaly_log import checked_dir, coders_in
from .coded_pages import check
from .model_coding import UNCLEAR, WHOLE, met, ticked_in
from .runlog import sha256


# ---- reading the coding page's exports ----

def evidence_segments(text: str) -> dict[str, set[int]]:
    """'trigger-24 @s05: "words" | ...' -> {code: {5}}"""
    out = {}
    for code, seg in re.findall(r'([\w-]+) @s(\d+): "', text or ""):
        out.setdefault(code, set()).add(int(seg))
    return out


def export_rows(path: Path) -> list[dict]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))["stories"]
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def from_export(cb: dict, rows: list[dict], n_segments: int) -> tuple[dict, list[str]]:
    """One interview's export -> the checked form the model's coding takes, and the problems found."""
    groups = {c: g["name"] for g in cb["groups"] for c in g["codes"]}
    pick = {c for g in cb["groups"] if g["pick_one"] for c in g["pick_one"]["codes"]}
    anomaly_ids = {g["anomaly"]["id"] for g in cb["groups"] if g["anomaly"]} | {cb["new"]["id"]}
    group_cols = [g["name"] for g in cb["groups"]]
    coded = {"overview": "", "stories": [], "decisions": [], "anomalies": [], "removed": []}
    problems, decisions = [], {}
    for r in rows:
        story = str(r.get("story") or "").strip()
        if story in ("", "0"):
            continue  # not coded yet, or nothing to code
        name = WHOLE if story == "W" else (r.get("story_name") or "").strip() or f"Story {story}"
        segs = {int(x) for x in re.findall(r"\d+", str(r.get("segments") or ""))}
        bad = sorted(x for x in segs if not 1 <= x <= n_segments)
        if bad:
            problems.append(f"{name}: segments {bad} are not in the interview")
            segs -= set(bad)
        ev = evidence_segments(r.get("evidence", ""))
        codes = [c.strip() for col in group_cols + ["anomaly_codes"] for c in str(r.get(col) or "").split(";") if c.strip()]
        for c in codes:
            if c not in groups and c not in pick and c not in anomaly_ids:
                problems.append(f"{name}: {c} is not a code in codebook {cb['version']}")
        cited = lambda c: sorted(ev.get(c) or segs)
        for c in codes:
            if c in (groups.keys() | anomaly_ids) and not ev.get(c):
                problems.append(f"{name}: {c} has no highlighted words; the story's segments are used")
        states = [c for c in codes if c in pick]
        if len(states) > 1:
            problems.append(f"{name}: more than one search state ({', '.join(states)}); the first is used")
        if name != WHOLE:
            coded["stories"].append({"name": name, "summary": r.get("summary", ""), "segments": sorted(segs),
                                     "search_state": states[0] if states else UNCLEAR, "search_state_reason": ""})
        for c in codes:
            if c in groups:
                decisions.setdefault(c, []).append({"story": name, "segments": cited(c)})
        notes = dict(re.findall(r"(ANO-[A-Z]{3}): (.*?)(?= \| ANO-|$)", r.get("anomaly_notes") or ""))
        for c in codes:
            if c in anomaly_ids:
                coded["anomalies"].append({"code": c, "story": name, "label": notes.get(c, "").strip(),
                                           "why": notes.get(c, "").strip(), "segments": cited(c)})
                if not notes.get(c, "").strip():
                    problems.append(f"{name}: {c} has no note on why no code fits")
    coded["decisions"] = [{"code": c, "reason": "", "ticks": t} for c, t in decisions.items()]
    return coded, problems


def load_coders(cb: dict, work: Path, cases: list[dict]) -> tuple[dict, dict, list[Path]]:
    """{coder: {case_id: checked coding}}, {coder: [problems]}, and every input file read."""
    n_segs = {c["case_id"]: len(json.loads((work / "checked" / f"{c['case_id']}.segments.json").read_text(encoding="utf-8")))
              for c in cases}
    coders, problems, inputs = {}, {}, []
    for c in cases:
        reply = work / "replies" / f"{c['case_id']}.json"
        if reply.exists():
            segs = json.loads((work / "checked" / f"{c['case_id']}.segments.json").read_text(encoding="utf-8"))
            coded = check(cb, c["case_id"], segs, json.loads(reply.read_text(encoding="utf-8")))
            (checked_dir(work, "model") / f"{c['case_id']}.json").write_text(json.dumps(coded, ensure_ascii=False, indent=1), encoding="utf-8")
            coders.setdefault("model", {})[c["case_id"]] = coded
            problems.setdefault("model", []).extend(f"{c['case_id']}: removed {x}" for x in coded["removed"])
            inputs.append(reply)
    for d in sorted(p for p in (work / "coders").glob("*") if p.is_dir()) if (work / "coders").exists() else []:
        name, rows = d.name, {}
        for f in sorted(list(d.glob("*.csv")) + list(d.glob("*.json"))):
            for r in export_rows(f):
                rows.setdefault(r.get("case_id", ""), []).append(r)
            inputs.append(f)
        out = checked_dir(work, name)
        out.mkdir(parents=True, exist_ok=True)
        for case_id, rs in rows.items():
            if case_id not in n_segs:
                problems.setdefault(name, []).append(f"{case_id}: not an interview in this round")
                continue
            coded, probs = from_export(cb, rs, n_segs[case_id])
            (out / f"{case_id}.json").write_text(json.dumps(coded, ensure_ascii=False, indent=1), encoding="utf-8")
            coders.setdefault(name, {})[case_id] = coded
            problems.setdefault(name, []).extend(f"{case_id}: {p}" for p in probs)
    return coders, problems, inputs


# ---- agreement ----

def kappa(pairs: list[tuple]) -> float | None:
    """Cohen's kappa: agreement beyond what the two coders' base rates would give."""
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    labels = {x for pair in pairs for x in pair}
    expected = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return None if expected == 1 else round((observed - expected) / (1 - expected), 3)


def used(coded: dict) -> dict[str, set[int]]:
    """Every level-1 code used in an interview (search state included), with the segments cited for it."""
    out = {}
    for d in coded["decisions"]:
        for t in d["ticks"]:
            out.setdefault(d["code"], set()).update(t["segments"])
    for s in coded["stories"]:
        if s["search_state"] != UNCLEAR:
            out.setdefault(s["search_state"], set()).update(s["segments"][:1])
    return out


def story_segments(coded: dict) -> dict[str, set[int]]:
    """Each story's segments: its own and every segment ticked under it."""
    out = {s["name"]: set(s["segments"]) for s in coded["stories"]}
    for d in coded["decisions"]:
        for t in d["ticks"]:
            if t["story"] in out:
                out[t["story"]].update(t["segments"])
    return out


def match_stories(a: dict, b: dict) -> list[tuple[str, str]]:
    """Pair the stories of two coders that share the most segments; each story is used once."""
    sa, sb = story_segments(a), story_segments(b)
    ranked = sorted(((len(x & y), i, j) for i, x in sa.items() for j, y in sb.items() if x & y), reverse=True)
    used_a, used_b, pairs = set(), set(), []
    for _, i, j in ranked:
        if i not in used_a and j not in used_b:
            used_a.add(i), used_b.add(j), pairs.append((i, j))
    return pairs


def agreement(cb: dict, num: dict, a: dict, b: dict) -> dict:
    shared = sorted(set(a) & set(b))
    codes = [c for g in cb["groups"] for c in (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]]
    group_of = {c: g["name"] for g in cb["groups"] for c in (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]}
    ua = {c: used(a[c]) for c in shared}
    ub = {c: used(b[c]) for c in shared}

    by_code = {}
    for code in codes:
        pairs = [(code in ua[c], code in ub[c]) for c in shared]
        both = [c for c in shared if code in ua[c] and code in ub[c]]
        overlap = [len(ua[c][code] & ub[c][code]) / len(ua[c][code] | ub[c][code]) for c in both if ua[c][code] | ub[c][code]]
        by_code[code] = {"no": num[code], "group": group_of[code], "both": len(both),
                         "only_a": sum(x and not y for x, y in pairs), "only_b": sum(y and not x for x, y in pairs),
                         "neither": sum(not x and not y for x, y in pairs), "kappa": kappa(pairs),
                         "segment_overlap": round(sum(overlap) / len(overlap), 3) if overlap else None}
    by_group = {}
    for g in cb["groups"]:
        pairs = [(code in ua[c], code in ub[c]) for code in codes if group_of[code] == g["name"] for c in shared]
        by_group[g["name"]] = {"agree": sum(x == y for x, y in pairs), "of": len(pairs), "kappa": kappa(pairs)}
    every = [(code in ua[c], code in ub[c]) for code in codes for c in shared]

    matched = {c: match_stories(a[c], b[c]) for c in shared}
    level2 = {}
    for r in cb["rules"]:
        story_pairs = [(met(r, ticked_in(a[c], x)), met(r, ticked_in(b[c], y))) for c in shared for x, y in matched[c]]
        case_pairs = [(any(met(r, ticked_in(a[c], s["name"])) for s in a[c]["stories"]),
                       any(met(r, ticked_in(b[c], s["name"])) for s in b[c]["stories"])) for c in shared]
        level2[r["id"]] = {"no": num[r["id"]], "name": r["name"],
                           "stories": {"agree": sum(x == y for x, y in story_pairs), "of": len(story_pairs),
                                       "met_a": sum(x for x, _ in story_pairs), "met_b": sum(y for _, y in story_pairs),
                                       "kappa": kappa(story_pairs)},
                           "interviews": {"agree": sum(x == y for x, y in case_pairs), "of": len(case_pairs),
                                          "met_a": sum(x for x, _ in case_pairs), "met_b": sum(y for _, y in case_pairs),
                                          "kappa": kappa(case_pairs)}}
    return {"interviews_coded_by_both": len(shared),
            "stories": {"a": sum(len(a[c]["stories"]) for c in shared), "b": sum(len(b[c]["stories"]) for c in shared),
                        "matched": sum(len(m) for m in matched.values())},
            "codes_overall": {"agree": sum(x == y for x, y in every), "of": len(every), "kappa": kappa(every)},
            "by_group": by_group, "by_code": by_code, "level2": level2}


def near_misses(cb: dict, num: dict, coders: dict) -> list[dict]:
    """Anomalies another coder covered with a code of the same group on the same segments."""
    group_codes = {g["anomaly"]["id"]: set(g["codes"]) for g in cb["groups"] if g["anomaly"]}
    rows = []
    for name, cases in coders.items():
        for case_id, coded in cases.items():
            for a in coded["anomalies"]:
                for other, ocases in coders.items():
                    if other == name or case_id not in ocases:
                        continue
                    mine = used(coded)  # a code the anomaly's own coder also ticked there is no miss
                    hits = sorted(c for c, segs in used(ocases[case_id]).items()
                                  if c in group_codes.get(a["code"], set()) and segs & set(a["segments"])
                                  and not mine.get(c, set()) & set(a["segments"]))
                    if hits:
                        rows.append({"case_id": case_id, "coder": name, "anomaly": num.get(a["code"], a["code"]),
                                     "story": a["story"], "label": a["label"], "segments": a["segments"], "other_coder": other,
                                     "other_codes": "; ".join(f"{num[c]} {cb['labels'][c]}" for c in hits)})
    return rows


def code_use(cb: dict, num: dict, coders: dict) -> list[dict]:
    codes = [c for g in cb["groups"] for c in (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]]
    return [{"no": num[c], "code": c, "label": cb["labels"][c],
             **{name: sum(c in used(x) for x in cases.values()) for name, cases in coders.items()}} for c in codes]


def write_csv(path: Path, rows: list[dict]) -> None:
    if rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def build(work: Path) -> dict:
    from .coded_pages import numbering, use_round
    cb = use_round(work)
    num, level2 = numbering(cb)
    num.update({r["id"]: r["no"] for r in level2})
    cases = json.loads((work / "cases.json").read_text(encoding="utf-8"))
    coders, problems, inputs = load_coders(cb, work, cases)
    out = work / "comparison"
    out.mkdir(exist_ok=True)
    pairs = {f"{x} vs {y}": agreement(cb, num, coders[x], coders[y]) for x, y in combinations(sorted(coders), 2)}
    report = {"codebook": cb["version"], "coders": {n: {"interviews": len(c), "stories": sum(len(x["stories"]) for x in c.values()),
                                                        "anomalies": sum(len(x["anomalies"]) for x in c.values()),
                                                        "problems": problems.get(n, [])} for n, c in coders.items()},
              "pairs": pairs}
    (out / "agreement.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    write_csv(out / "codes.csv", [{"pair": p, "code": c, **v} for p, r in pairs.items() for c, v in r["by_code"].items()])
    write_csv(out / "level2.csv", [{"pair": p, "rule": k, "no": v["no"], "name": v["name"],
                                    **{f"stories_{x}": y for x, y in v["stories"].items()},
                                    **{f"interviews_{x}": y for x, y in v["interviews"].items()}}
                                   for p, r in pairs.items() for k, v in r["level2"].items()])
    write_csv(out / "near_misses.csv", near_misses(cb, num, coders))
    write_csv(out / "code_use.csv", code_use(cb, num, coders))
    (out / "manifest.json").write_text(json.dumps({
        "made": datetime.now(timezone.utc).isoformat(timespec="seconds"), "codebook": cb["version"],
        "inputs": {str(p.relative_to(work)): sha256(p) for p in inputs}}, indent=1), encoding="utf-8")
    return report


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    report = build(Path(sys.argv[1]))
    for name, info in report["coders"].items():
        print(f"{name}: {info['interviews']} interviews, {info['stories']} stories, {info['anomalies']} anomalies, "
              f"{len(info['problems'])} problems")
        for p in info["problems"][:20]:
            print(f"  {p}")
    for pair, r in report["pairs"].items():
        print(f"{pair}: {r['interviews_coded_by_both']} interviews; codes agree {r['codes_overall']['agree']}/"
              f"{r['codes_overall']['of']} (kappa {r['codes_overall']['kappa']}); stories {r['stories']['a']} and "
              f"{r['stories']['b']}, {r['stories']['matched']} matched")
        print("  level 2 per interview: " + ", ".join(f"{v['no']} {v['interviews']['agree']}/{v['interviews']['of']}"
                                                      for v in r["level2"].values()))


if __name__ == "__main__":
    main()
