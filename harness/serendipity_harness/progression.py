"""How the codebook grew: every code against every codebook version.

Usage: python -m serendipity_harness.progression OUT_DIR

Reads every harness/codebook/codebook_v<version>.json and the anomaly log, and
writes OUT_DIR/codebook_progression.html (one page, for readers) and
codebook_progression.csv. One row per code, one column per version, ticked where
the code is in that version, with where it came from (the papers that state it,
or the anomaly theme it grew out of; a code no paper states is marked inductive)
and what changed (added, wording revised, dropped). A version's file may give a
code a "change_note" with the reason.

The page sets the versions side by side: one row per group, each version's codes
in its own column, level 1 then level 2. Added codes are shaded green with their
papers, revised ones yellow, dropped ones red. The last rows list the papers each
version adds and the counts per version.
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

from .model_coding import codebook_from
from .runlog import HARNESS

E = html.escape
KIND_LETTER = {"definition": "D", "rival": "R", "type": "T", "judgment": "J"}
WORDING = ("label", "definition", "applies_when", "does_not_apply_when")


def versions() -> list[dict]:
    files = sorted(HARNESS.glob("codebook/codebook_v*.json"),
                   key=lambda p: [int(x) for x in re.findall(r"\d+", p.stem)])
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def level1(raw: dict) -> dict:
    """Code id -> (number, group title, the code) for one version's level-1 codes, numbered as in the codebook."""
    cb = codebook_from(raw)
    out = {}
    for gi, g in enumerate(cb["groups"], 1):
        pick = g["pick_one"]["codes"] if g["pick_one"] else []
        for k, c in enumerate(pick + g["codes"], 1):
            out[c] = (f"{gi}.{k}", g["title"], cb["codes"][c])
    return out


def level2(raw: dict) -> dict:
    out, count = {}, {}
    for r in raw["levels"]["level2"]:
        letter = KIND_LETTER[r["kind"]]
        count[letter] = count.get(letter, 0) + 1
        out[r["id"]] = (f"{letter}{count[letter]}", r)
    return out


def state(i: int, key: str, per: list[dict], wording) -> str:
    """What happened to a code or rule in version i: new, revised, same, dropped, or "" (not there)."""
    now, before = key in per[i], i > 0 and key in per[i - 1]
    if now and i and not before:
        return "new"
    if now and before and wording(per[i - 1][key]) != wording(per[i][key]):
        return "revised"
    if now:
        return "same"
    return "dropped" if before else ""


def rule_papers(rule: dict, l1: dict, raw: dict) -> list[str]:
    """The papers behind a level-2 item: those of its own sentences, or of the drafted codes it came from."""
    if rule.get("evidence"):
        return list(dict.fromkeys(e["passage_id"].split(":")[0] for e in rule["evidence"]))
    codes = {c["id"]: c for c in raw["codes"]} if isinstance(raw["codes"], list) else raw["codes"]
    return list(dict.fromkeys(p for c in rule.get("evidence_from", []) for p in codes.get(c, {}).get("papers", [])))


def cite(pid: str, meta: dict) -> str:
    m = meta.get(pid)
    return f'{m["file_author"]} {m["file_year"]}' if m else pid


def build(out: Path) -> dict:
    vs = versions()
    names = [v["version"] for v in vs]
    meta = json.loads((HARNESS / "codebook" / "paper_metadata.json").read_text(encoding="utf-8"))
    log_file = HARNESS / "codebook" / "anomaly_log.json"
    log = json.loads(log_file.read_text(encoding="utf-8")) if log_file.exists() else {"themes": []}
    adopted = {(t["version"], t["code"]): t for t in log["themes"] if t["status"] == "adopted"}
    l1 = [level1(v) for v in vs]
    l2 = [level2(v) for v in vs]

    rows, order = [], []
    for per in l1:
        order += [c for c in per if c not in order]
    for cid in order:
        present = [cid in per for per in l1]
        last = max(i for i, p in enumerate(present) if p)
        no, group, code = l1[last][cid]
        first = present.index(True)
        theme = code.get("from_theme") or next((t["id"] for (v, n), t in adopted.items()
                                                 if v == names[first] and n == l1[first][cid][0]), None)
        papers = code.get("papers", [])
        if theme:
            source = f"Round anomalies: {theme}" + (f"; {len(papers)} papers" if papers else "; no paper (inductive)")
        else:
            source = f"Literature: {len(papers)} papers"
        changes = []
        for i in range(1, len(vs)):
            before, now = cid in l1[i - 1], cid in l1[i]
            note = (l1[i][cid][2].get("change_note") if now else "") or ""
            if now and not before:
                changes.append(f"v{names[i]}: added" + (f" ({note})" if note else ""))
            elif before and not now:
                gone = next((r for r in vs[i].get("rejected", []) if r.get("id") == cid), {})
                changes.append(f"v{names[i]}: dropped" + (f" ({gone.get('reason') or note})" if gone.get("reason") or note else ""))
            elif now and any(l1[i - 1][cid][2].get(k) != l1[i][cid][2].get(k) for k in WORDING):
                changes.append(f"v{names[i]}: wording revised" + (f" ({note})" if note else ""))
        status = [state(i, cid, l1, lambda x: tuple(x[2].get(k) for k in WORDING)) for i in range(len(vs))]
        pids = [list(l1[i][cid][2].get("papers", [])) if present[i] else [] for i in range(len(vs))]
        rows.append({"level": 1, "no": no, "group": group, "id": cid, "label": code["label"], "present": present,
                     "status": status, "pids": pids, "theme": theme,
                     "labels": [l1[i][cid][2]["label"] if present[i] else code["label"] for i in range(len(vs))], "notes": [
                         ((l1[i][cid][2].get("change_note") if present[i] else next(
                             (r.get("reason") for r in vs[i].get("rejected", []) if r.get("id") == cid), "")) or "")
                         for i in range(len(vs))],
                     "source": source, "papers": "; ".join(dict.fromkeys(cite(p, meta) for p in papers)), "change": "; ".join(changes),
                     "key": (tuple(int(x) for x in no.split(".")), -last)})
    rows.sort(key=lambda r: r["key"])  # each code under its group, by its latest number; a dropped code after the one now holding its number
    order2 = []
    for per in l2:
        order2 += [r for r in per if r not in order2]
    for rid in order2:
        present = [rid in per for per in l2]
        last = max(i for i, p in enumerate(present) if p)
        no, r = l2[last][rid]
        status = [state(i, rid, l2, lambda x: tuple(tuple(x[1].get(k, [])) for k in ("all", "any", "none"))) for i in range(len(vs))]
        pids = [rule_papers(l2[i][rid][1], l1[i], vs[i]) if present[i] else [] for i in range(len(vs))]
        rows.append({"level": 2, "no": no, "group": r["kind"].capitalize(), "id": rid,
                     "label": f'{r["name"]}: {r.get("in_short", "")}'.rstrip(": "), "present": present,
                     "status": status, "pids": pids, "theme": None, "notes": [""] * len(vs),
                     "labels": [f'{l2[i][rid][1]["name"]}: {l2[i][rid][1].get("in_short", "")}'.rstrip(": ") if present[i] else r["name"]
                                for i in range(len(vs))],
                     "source": "Rule over level-1 codes" if r["kind"] != "judgment" else "Decided by the researchers",
                     "papers": "", "change": ""})

    counts = []
    for i, v in enumerate(vs):
        mine = [r for r in rows if r["level"] == 1 and r["present"][i]]
        counts.append({"version": v["version"], "level1": len(mine),
                       "from_literature": sum(not r["source"].startswith("Round") for r in mine),
                       "from_anomalies": sum(r["source"].startswith("Round") for r in mine),
                       "level2": sum(r["level"] == 2 and r["present"][i] for r in rows),
                       "themes_adopted": sum(1 for (ver, _) in adopted if ver == v["version"])})
    open_themes = sum(t["status"] == "open" for t in log["themes"])
    held = [set().union(*(r["pids"][i] for r in rows)) for i in range(len(vs))]
    for i, c in enumerate(counts):
        c["papers"] = len(held[i])
        c["papers_added"] = sorted(cite(p, meta) for p in held[i] - (held[i - 1] if i else set()))
        c["papers_removed"] = sorted(cite(p, meta) for p in (held[i - 1] - held[i] if i else set()))
    for r in rows:
        r["cites"] = ["; ".join(dict.fromkeys(cite(p, meta) for p in ids)) for ids in r["pids"]]

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "codebook_progression.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["level", "no", "group", "code_id", "label", *[f"v{n}" for n in names], "source", "papers", "change"])
        for r in rows:
            w.writerow([r["level"], r["no"], r["group"], r["id"], r["label"], *["x" if p else "" for p in r["present"]],
                        r["source"], r["papers"], r["change"]])
    (out / "codebook_progression.html").write_text(page(vs, rows, counts, open_themes), encoding="utf-8")
    return {"versions": names, "codes": len(rows), "open_themes": open_themes}


def page(vs: list[dict], rows: list[dict], counts: list[dict], open_themes: int) -> str:
    """Versions side by side: one row per group, each version's codes in its own column."""
    names = [v["version"] for v in vs]
    heads = "".join(f"<th>v{E(n)}</th>" for n in names)
    groups = list(dict.fromkeys((r["level"], r["group"]) for r in rows))
    tag = {"new": "added", "revised": "revised", "dropped": "dropped"}
    body = []
    for level in (1, 2):
        body.append(f'<tr class=lvl><td colspan="{1 + len(names)}">Level {level}: '
                    f'{"codes the coders tick" if level == 1 else "worked out from the level-1 codes, story by story"}</td></tr>')
        for lv, g in groups:
            if lv != level:
                continue
            for i in range(len(names)):
                items = []
                for r in rows:
                    if (r["level"], r["group"]) != (lv, g) or not r["status"][i]:
                        continue
                    st = r["status"][i]
                    extra = ""
                    if st in tag:
                        why = r["notes"][i] or ("from the round's anomalies" if r["theme"] and st == "new" else "")
                        extra = f'<span class=t>{tag[st]}</span>' + (f'<div class=why>{E(why)}</div>' if why else "")
                        if st == "new":
                            extra += f'<div class=why>{"Papers: " + E(r["cites"][i]) if r["cites"][i] else "No paper: inductive, from the data"}</div>'
                    items.append(f'<li class="{st}" title="{E(r["cites"][i] or (r["cites"][i - 1] if i else ""))}">'
                                 f'<span class=no>{E(r["no"])}</span> <span class=lab>{E(r["labels"][i])}</span>{extra}</li>')
                cells_html = f'<ul>{"".join(items)}</ul>' if items else '<span class=muted>none</span>'
                body.append(("" if i else f'<tr><th class=g>{E(g)}</th>') + f"<td>{cells_html}</td>")
            body.append("</tr>")
    def plist(xs):
        return f'<details><summary>{len(xs)} paper{"s" * (len(xs) != 1)}</summary><p class=pl>{E("; ".join(xs))}</p></details>' if xs else '<span class=muted>none</span>'
    papers = ('<tr class=sum><th class=g>Papers added</th>'
              + "".join(f'<td>{"<b>Starting set:</b> " if i == 0 else ""}{plist(c["papers_added"])}'
                        + (f'<div class=why>Papers no longer cited: {E("; ".join(c["papers_removed"]))}</div>' if c["papers_removed"] else "")
                        + "</td>" for i, c in enumerate(counts)) + "</tr>")
    count_rows = [("Paper files cited by these codes", "papers"), ("Level-1 codes", "level1"), ("from the literature", "from_literature"),
                  ("from round anomalies", "from_anomalies"), ("Level-2 items", "level2"), ("Anomaly themes adopted", "themes_adopted")]
    foot = papers + "".join(f'<tr class=sum><th class=g>{E(lab)}</th>' + "".join(f"<td class=n>{c[k]}</td>" for c in counts) + "</tr>"
                            for lab, k in count_rows)
    return TEMPLATE.format(construct=E(vs[-1].get("construct", "")), versions=", ".join(f"v{E(n)}" for n in names),
                           heads=heads, body="".join(body), foot=foot, open_themes=open_themes)


TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codebook progression</title><style>
:root {{ --bg:#fff; --fg:#1d2329; --muted:#5d6670; --line:#d5dbe1; --panel:#f6f8fa; --head:#1f3a5f;
  --new:#e3f2e5; --newfg:#1e6b35; --rev:#fff3c4; --revfg:#7a5b00; --drop:#fde2e2; --dropfg:#b42318; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42;
  --panel:#1a1f25; --head:#8fb3e0; --new:#1d3324; --newfg:#7fd39a; --rev:#3a3420; --revfg:#e0c060; --drop:#3d1f1f; --dropfg:#ff8a80; }} }}
:root[data-theme="dark"] {{ --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42; --panel:#1a1f25; --head:#8fb3e0;
  --new:#1d3324; --newfg:#7fd39a; --rev:#3a3420; --revfg:#e0c060; --drop:#3d1f1f; --dropfg:#ff8a80; }}
body {{ margin:0; padding:16px; background:var(--bg); color:var(--fg); font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; }}
h1 {{ font-size:20px; margin:0 0 6px; color:var(--head); }} p.lead {{ max-width:900px; color:var(--muted); margin:4px 0 8px; }}
.key {{ display:flex; gap:12px; flex-wrap:wrap; font-size:13px; margin:0 0 12px; }} .key span {{ padding:1px 8px; border-radius:4px; }}
.wrap {{ overflow-x:auto; }} table {{ border-collapse:collapse; min-width:100%; }}
th,td {{ border:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }}
thead th {{ background:var(--panel); position:sticky; top:0; min-width:260px; }} thead th:first-child {{ min-width:120px; }}
th.g {{ background:var(--panel); color:var(--head); width:140px; }}
tr.lvl td {{ background:var(--head); color:var(--bg); font-weight:600; }}
ul {{ list-style:none; margin:0; padding:0; }} li {{ padding:2px 6px; border-radius:4px; margin:1px 0; }}
li.new {{ background:var(--new); }} li.revised {{ background:var(--rev); }} li.dropped {{ background:var(--drop); color:var(--dropfg); }} li.dropped .lab {{ text-decoration:line-through; }}
.no {{ display:inline-block; min-width:32px; color:var(--muted); font-variant-numeric:tabular-nums; }}
.t {{ font-size:11px; font-weight:600; margin-left:6px; text-transform:uppercase; }} li.new .t {{ color:var(--newfg); }} li.revised .t {{ color:var(--revfg); }}
.why {{ font-size:12px; color:var(--muted); margin-left:38px; text-decoration:none; }} .muted {{ color:var(--muted); }}
tr.sum td.n {{ font-weight:600; }} details summary {{ cursor:pointer; color:var(--head); }} .pl {{ font-size:12px; margin:4px 0; }}
li[title] {{ cursor:help; }}
</style></head><body>
<h1>How the codebook grew</h1>
<p class=lead>Each {construct} codebook version side by side ({versions}). The first version was built from the papers. Each later version adds codes for anomaly themes that recurred in the round before it, and may revise or drop codes; the papers behind each added code are listed with it. Hover a code for its papers. Anomaly themes still open, carried forward to the next round: {open_themes}.</p>
<div class=key><span style="background:var(--new)">added</span><span style="background:var(--rev)">wording or rule revised</span><span style="background:var(--drop)">dropped</span></div>
<div class=wrap><table><thead><tr><th>Group</th>{heads}</tr></thead>
<tbody>{body}</tbody><tfoot>{foot}</tfoot></table></div>
</body></html>
"""


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(json.dumps(build(Path(sys.argv[1]))))


if __name__ == "__main__":
    main()
