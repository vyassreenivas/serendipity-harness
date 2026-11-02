"""Check coding replies and write one highlighted page per interview.

Usage: python -m serendipity_harness.coded_pages WORK_DIR OUT_DIR

WORK_DIR holds cases.json, replies/<case_id>.json (one InterviewCoding reply per
interview, from the coder prompt) and checked/<case_id>.segments.json (the
interview's numbered segments). Each reply goes through the same checks as
model_coding (Checker, check_interview); what they remove is recorded. Level 2 is
then worked out story by story from the checked ticks.

Each page shows every code on the left (the level-1 codes by group, the anomaly
codes, and the 11 level-2 items), marked with the stories that use it (S1, S2;
W for the whole journey), and the stories with the level-2 items each meets.
On the right is the interview, each coded segment highlighted and tagged with
its code numbers and story. Anomalies are red. The pages hold the full interview text: keep
them out of git and never publish them.
"""
from __future__ import annotations

import html
import json
import sys
import tomllib
from pathlib import Path

from .model_coding import WHOLE, Checker, InterviewCoding, check_interview, codebook_from, met, ticked_in
from .runlog import HARNESS

E = html.escape
KIND_LETTER = {"definition": "D", "rival": "R", "type": "T", "judgment": "J"}
KIND_TITLE = {"definition": "Definitions", "rival": "Rival explanations", "type": "Types", "judgment": "Decided by the researchers"}


class _Run:  # load_codebook reads only the run's configuration
    def config(self):
        return tomllib.loads((HARNESS / "project.toml").read_text(encoding="utf-8"))


def numbering(cb: dict) -> tuple[dict, list[dict]]:
    """Code id -> number as in the codebook document (2.3; 2.A for anomalies; D1 for level 2)."""
    num = {}
    for gi, g in enumerate(cb["groups"], 1):
        pick = g["pick_one"]["codes"] if g["pick_one"] else []
        for k, c in enumerate(pick + g["codes"], 1):
            num[c] = f"{gi}.{k}"
        if g["anomaly"]:
            num[g["anomaly"]["id"]] = f"{gi}.A"
    num[cb["new"]["id"]] = f"{len(cb['groups']) + 1}.A"
    level2, count = [], {}
    for r in json.loads((HARNESS / cb_path()).read_text(encoding="utf-8"))["levels"]["level2"]:
        letter = KIND_LETTER[r["kind"]]
        count[letter] = count.get(letter, 0) + 1
        level2.append(dict(r, no=f"{letter}{count[letter]}"))
    return num, level2


_round_codebook = None  # set by use_round


def cb_path() -> str:
    return _round_codebook or _Run().config()["coding"]["codebook"].removeprefix("harness/")


def use_round(work: Path) -> dict:
    """The codebook a round was set up with (its round.json, written by rounds.py), else project.toml's."""
    global _round_codebook
    r = work / "round.json"
    _round_codebook = json.loads(r.read_text(encoding="utf-8"))["codebook"].removeprefix("harness/") if r.exists() else None
    return codebook_from(json.loads((HARNESS / cb_path()).read_text(encoding="utf-8")))


def check(cb: dict, case_id: str, segments: list[dict], reply: dict) -> dict:
    got = InterviewCoding.model_validate(reply)
    chk = Checker(case_id, len(segments))
    coded = check_interview(chk, cb, got.overview, got.stories, got.decisions, got.anomalies)
    return dict(coded, removed=chk.removed)


def page(cb: dict, num: dict, level2: list[dict], case: dict, segments: list[dict], coded: dict) -> str:
    label = cb["labels"]
    tag = {s["name"]: f"S{k}" for k, s in enumerate(coded["stories"], 1)} | {WHOLE: "W"}
    tags = {k: [] for k in range(1, len(segments) + 1)}  # segment -> [(story tag, code, reason, anomaly)]
    used = {}  # code -> [(story tag, reason)]
    for st in coded["stories"]:
        if st["search_state"] != "unclear":
            for x in st["segments"][:1]:
                tags[x].append((tag[st["name"]], st["search_state"], st["search_state_reason"], False))
            used.setdefault(st["search_state"], []).append((tag[st["name"]], st["search_state_reason"]))
    for d in coded["decisions"]:
        for t in d["ticks"]:
            for x in t["segments"]:
                tags[x].append((tag[t["story"]], d["code"], d["reason"], False))
            used.setdefault(d["code"], []).append((tag[t["story"]], d["reason"]))
    for a in coded["anomalies"]:
        for x in a["segments"]:
            tags[x].append((tag[a["story"]], a["code"], f"{a['label']}: {a['why']}", True))
        used.setdefault(a["code"], []).append((tag[a["story"]], f"{a['label']}: {a['why']}"))

    def code_row(cid, anomaly=False):
        hits = used.get(cid, [])
        cls = "code" + (" on" if hits else "") + (" ano" if anomaly else "")
        why = " | ".join(f"{s}: {r}" for s, r in dict.fromkeys(hits))
        marks = "".join(f'<span class="ep">{s}</span>' for s in dict.fromkeys(s for s, _ in hits))
        name = "None of these fits" if anomaly else label[cid]
        return (f'<li class="{cls}" data-code="{E(cid)}" title="{E(why)}"><span class="no">{num[cid]}</span>'
                f'<span class="lab">{E(name)}</span>{marks}</li>')

    left = []
    if coded["stories"]:
        rows = []
        for st in coded["stories"]:
            hit = [r["no"] for r in level2 if r["kind"] != "judgment" and met(r, ticked_in(coded, st["name"]))]
            rows.append(f'<li class="story"><b>{tag[st["name"]]}</b> {E(st["name"])}'
                        f'<span class="l2">{E(", ".join(hit)) or "no level-2 item"}</span></li>')
        left.append(f'<h3>Stories</h3><ul>{"".join(rows)}</ul>')
    for gi, g in enumerate(cb["groups"], 1):
        rows = []
        if g["pick_one"]:
            rows.append(f'<li class="sub">{E(g["pick_one"]["name"])} (pick one, per story)</li>')
            rows += [code_row(c) for c in g["pick_one"]["codes"]]
            rows.append('<li class="sub">Parts present</li>')
        rows += [code_row(c) for c in g["codes"]]
        if g["anomaly"]:
            rows.append(code_row(g["anomaly"]["id"], anomaly=True))
        left.append(f'<h3>{gi}. {E(g["title"])}</h3><ul>{"".join(rows)}</ul>')
    left.append(f'<h3>{len(cb["groups"]) + 1}. Something else</h3><ul>{code_row(cb["new"]["id"], anomaly=True)}</ul>')
    l2rows, kind = [], None
    for r in level2:
        if r["kind"] != kind:
            kind = r["kind"]
            l2rows.append(f'<li class="sub">{KIND_TITLE[kind]}</li>')
        if r["kind"] == "judgment":
            l2rows.append(f'<li class="code l2 judg"><span class="no">{r["no"]}</span><span class="lab">{E(r["name"])}</span>'
                          f'<span class="note">researchers decide</span></li>')
            continue
        hit = [tag[st["name"]] for st in coded["stories"] if met(r, ticked_in(coded, st["name"]))]
        l2rows.append(f'<li class="code l2{" on" if hit else ""}"><span class="no">{r["no"]}</span><span class="lab">{E(r["name"])}</span>'
                      + "".join(f'<span class="ep">{t}</span>' for t in hit) + "</li>")
    left.append(f'<h3>Level 2: worked out per story</h3><ul>{"".join(l2rows)}</ul>')

    right = []
    for k, sg in enumerate(segments, 1):
        chips = "".join(f'<span class="tag{" ano" if a else ""}" title="{st}: {E(r)}">{num[c]}<small>{st}</small></span>'
                        for st, c, r, a in tags[k])
        cls = "seg" + (" coded" if tags[k] else "") + (" hasano" if any(t[3] for t in tags[k]) else "")
        role = {"question": "Q", "answer": "A"}.get(sg["role"], "")
        right.append(f'<div class="{cls}" id="s{k}" data-codes="{" ".join(dict.fromkeys(c for _, c, _, _ in tags[k]))}">'
                     f'<div class="meta"><span class="sn">[{k}]</span>{role}{chips}</div>'
                     f'<div class="txt">{E(sg["text"])}</div></div>')
    stories = "".join(f'<li><b>{tag[st["name"]]} {E(st["name"])}</b>: {E(st["summary"])}</li>' for st in coded["stories"])
    removed = "".join(f"<li>{E(r)}</li>" for r in coded["removed"])
    n = len(coded["stories"])
    summary = (f'<p><b>{n} stor{"y" if n == 1 else "ies"}.</b> {E(coded["overview"])}</p>'
               + (f'<ul class="stories">{stories}</ul>' if stories else "")
               + (f'<details><summary>Removed by the checks ({len(coded["removed"])})</summary><ul>{removed}</ul></details>' if removed else ""))
    return PAGE.format(title=E(case["file"].removesuffix(".txt")), case_no=case["case_no"], summary=summary,
                       left="".join(left), right="".join(right))


def build(work: Path, out: Path) -> None:
    cb = use_round(work)
    num, level2 = numbering(cb)
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((work / "cases.json").read_text(encoding="utf-8"))
    index, all_anos = [], []
    for case in cases:
        reply_path = work / "replies" / f"{case['case_id']}.json"
        if not reply_path.exists():
            print(f"{case['case_id']}: no reply yet")
            continue
        segments = json.loads((work / "checked" / f"{case['case_id']}.segments.json").read_text(encoding="utf-8"))
        coded = check(cb, case["case_id"], segments, json.loads(reply_path.read_text(encoding="utf-8")))
        (work / "checked" / f"{case['case_id']}.json").write_text(json.dumps(coded, ensure_ascii=False, indent=1), encoding="utf-8")
        name = f"{case['case_no']}_{case['file'].removesuffix('.txt')}.html"
        (out / name).write_text(page(cb, num, level2, case, segments, coded), encoding="utf-8")
        per = [f"S{k}: " + (", ".join(r["no"] for r in level2 if r["kind"] != "judgment" and met(r, ticked_in(coded, st["name"]))) or "none")
               for k, st in enumerate(coded["stories"], 1)]
        anos = len(coded["anomalies"])
        index.append((case, name, len(coded["stories"]), per, anos, len(coded["removed"])))
        for a in coded["anomalies"]:
            all_anos.append(dict(a, case=case, page=name))
        print(f"{case['case_no']} {case['case_id']}: {len(coded['stories'])} stories, {'; '.join(per)}, "
              f"{anos} anomalies, {len(coded['removed'])} removed")
    rows = "".join(f'<tr><td>{c["case_no"]}</td><td><a href="{E(n)}">{E(c["file"].removesuffix(".txt"))}</a></td>'
                   f'<td>{e}</td><td>{E("; ".join(m)) or "none"}</td><td>{a}</td><td>{r}</td></tr>'
                   for c, n, e, m, a, r in index)
    (out / "index.html").write_text(INDEX.format(rows=rows, n=len(index)), encoding="utf-8")
    themes_file = work / "anomaly_themes.json"
    themes = json.loads(themes_file.read_text(encoding="utf-8"))["themes"] if themes_file.exists() else []
    (out / "anomalies.html").write_text(anomalies_page(cb, num, all_anos, themes), encoding="utf-8")
    print(f"anomalies.html: {len(all_anos)} anomalies, {len(themes)} candidate codes")


def anomalies_page(cb: dict, num: dict, anos: list[dict], themes: list[dict]) -> str:
    """Every anomaly (A01, A02, ... in interview order), and the candidate inductive codes they suggest.
    Each candidate says whether a code drafted from the papers already states it."""
    for k, a in enumerate(anos, 1):
        a["id"] = f"A{k:02d}"
    by_id = {a["id"]: a for a in anos}
    drafted = {c["id"]: c for c in json.loads((HARNESS / cb_path()).read_text(encoding="utf-8"))["codes"]}
    link = lambda a: f'<a href="{E(a["page"])}#s{a["segments"][0]}">{a["id"]}</a>'
    trows = []
    for t in themes:
        ids = [i.removeprefix("model:") for i in t["anomalies"] if i.removeprefix("model:") in by_id]  # the model's only
        cases = sorted({by_id[i]["case"]["case_no"] for i in ids})
        near = "".join(f'<li>{E(c)}: {E(drafted[c]["label"])} <span class="muted">({len(drafted[c]["papers"])} papers)</span></li>'
                       for c in t["nearest"] if c in drafted) or '<li class="muted">none among the drafted codes</li>'
        new = not t["nearest"]
        trows.append(f'<tr class="{"new" if new else ""}"><td><b>{E(t["name"])}</b><br><span class="muted">{E(t["group"])}</span></td>'
                     f'<td>{E(t["what"])}</td><td>{", ".join(link(by_id[i]) for i in ids)}<br><span class="muted">'
                     f'{len(cases)} interview{"s" * (len(cases) != 1)}</span></td><td><ul>{near}</ul></td><td>{E(t["verdict"])}</td></tr>')
    arows = "".join(f'<tr><td>{link(a)}</td><td>{num[a["code"]]} <span class="muted">{E(a["code"])}</span></td>'
                    f'<td>{E(a["case"]["file"].removesuffix(".txt"))}<br><span class="muted">{E(a["story"])}</span></td>'
                    f'<td><b>{E(a["label"])}</b><br>{E(a["why"])}</td><td>{", ".join(map(str, a["segments"]))}</td></tr>'
                    for a in anos)
    return ANOS.format(n=len(anos), m=len(themes), trows="".join(trows), arows=arows)


STYLE = """
:root { --bg:#fff; --fg:#1d2329; --muted:#5d6670; --line:#d5dbe1; --panel:#f6f8fa; --hi:#fff3c4; --hiline:#e0b400;
        --on:#dff0e3; --onfg:#1e6b35; --ano:#fde2e2; --anofg:#b42318; --ep:#eef2f6; --head:#1f3a5f; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42;
        --panel:#1a1f25; --hi:#3a3420; --hiline:#c9a227; --on:#1d3324; --onfg:#7fd39a; --ano:#3d1f1f; --anofg:#ff8a80; --ep:#1c232b; --head:#8fb3e0; } }
:root[data-theme="dark"] { --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42; --panel:#1a1f25; --hi:#3a3420; --hiline:#c9a227;
        --on:#1d3324; --onfg:#7fd39a; --ano:#3d1f1f; --anofg:#ff8a80; --ep:#1c232b; --head:#8fb3e0; }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif; }
a { color:var(--head); }
"""

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{case_no} {title}</title><style>""" + STYLE.replace("{", "{{").replace("}", "}}") + """
header {{ padding:12px 16px; border-bottom:1px solid var(--line); }} header h1 {{ font-size:18px; margin:0 0 4px; }} header p {{ margin:4px 0; color:var(--muted); }}
.wrap {{ display:flex; }} aside {{ width:340px; flex:none; background:var(--panel); border-right:1px solid var(--line); padding:8px 12px;
  height:calc(100vh - 0px); position:sticky; top:0; overflow:auto; }}
main {{ flex:1; padding:12px 16px; max-width:900px; }}
aside h3 {{ font-size:13px; margin:12px 0 4px; color:var(--head); }} aside ul {{ list-style:none; margin:0; padding:0; }}
li.code {{ display:flex; gap:6px; align-items:baseline; padding:2px 6px; border-radius:4px; cursor:pointer; color:var(--muted); }}
li.code.on {{ background:var(--on); color:var(--onfg); font-weight:600; }} li.code.ano {{ font-style:italic; }}
li.code.ano.on {{ background:var(--ano); color:var(--anofg); }} li.code.judg {{ cursor:default; }}
li.sub {{ font-size:12px; color:var(--muted); margin-top:4px; }} .no {{ min-width:30px; font-variant-numeric:tabular-nums; }}
.lab {{ flex:1; }} .ep {{ font-size:11px; border:1px solid currentColor; border-radius:6px; padding:0 4px; }} .note {{ font-size:11px; }}
.seg {{ border-left:3px solid transparent; padding:6px 10px; margin:4px 0; border-radius:4px; }}
.seg.inep {{ background:var(--ep); }} .seg.coded {{ border-left-color:var(--hiline); background:var(--hi); }} .seg.hasano {{ border-left-color:var(--anofg); }}
.seg.flash {{ outline:2px solid var(--head); }}
.meta {{ font-size:12px; color:var(--muted); display:flex; gap:4px; flex-wrap:wrap; align-items:center; }} .sn {{ font-weight:600; }}
.tag {{ background:var(--on); color:var(--onfg); border-radius:4px; padding:0 5px; font-weight:600; }}
.tag.ano {{ background:var(--ano); color:var(--anofg); }} .tag small {{ font-weight:400; margin-left:3px; opacity:.8; }}
li.story {{ display:flex; gap:6px; padding:2px 6px; }} li.story .l2 {{ margin-left:auto; font-size:12px; color:var(--onfg); }}
ul.stories {{ margin:4px 0; padding-left:20px; }}
.txt {{ white-space:pre-wrap; }} .epbox {{ margin:14px 0 4px; padding:8px 10px; border:1px solid var(--line); border-radius:6px; background:var(--panel); }}
@media (max-width:760px) {{ .wrap {{ display:block; }} aside {{ width:auto; height:auto; position:static; }} }}
</style></head><body>
<header><h1>{case_no}. {title}</h1>{summary}
<p>The whole interview is coded; every tick belongs to a story (S1, S2; W for remarks about the whole journey), and level 2 is worked out story by story. Left: the stories with the level-2 items each meets, then every code, green where it is used (red for anomalies) with its stories. Hover for the coder's reason; click a code to find its segments. Right: the interview; highlighted segments carry their code numbers and story. Coded by Claude Opus 5.5 in a Claude Code session (not the API) with the harness's coder prompt and checks.</p></header>
<div class="wrap"><aside>{left}</aside><main>{right}</main></div>
<script>
let i = 0, last = null;
document.querySelectorAll("li.code[data-code]").forEach(li => li.onclick = () => {{
  const segs = [...document.querySelectorAll(".seg")].filter(s => s.dataset.codes.split(" ").includes(li.dataset.code));
  if (!segs.length) return;
  i = (last === li.dataset.code) ? (i + 1) % segs.length : 0; last = li.dataset.code;
  document.querySelectorAll(".flash").forEach(s => s.classList.remove("flash"));
  segs[i].classList.add("flash"); segs[i].scrollIntoView({{behavior:"smooth", block:"center"}});
}});
</script></body></html>
"""

INDEX = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coded interviews</title><style>""" + STYLE.replace("{", "{{").replace("}", "}}") + """
body {{ padding:16px; }} table {{ border-collapse:collapse; width:100%; max-width:1000px; }}
th,td {{ border:1px solid var(--line); padding:6px 8px; text-align:left; }} th {{ background:var(--panel); }}
</style></head><body><h1>Coded interviews ({n})</h1>
<p>Coded by Claude Opus 5.5 in a Claude Code session (not the API) with the harness's coder prompt and checks. Level 2 is worked out per story.</p>
<p><a href="anomalies.html">Anomalies and candidate inductive codes</a></p>
<table><tr><th>No.</th><th>Interview</th><th>Stories</th><th>Level 2 met, per story</th><th>Anomalies</th><th>Removed by checks</th></tr>{rows}</table></body></html>
"""

ANOS = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anomalies</title><style>""" + STYLE.replace("{", "{{").replace("}", "}}") + """
body {{ padding:16px; max-width:1200px; margin:0 auto; }} .wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; min-width:720px; margin-bottom:24px; }}
th,td {{ border:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }} th {{ background:var(--panel); }}
td ul {{ margin:0; padding-left:16px; }} .muted {{ color:var(--muted); font-size:12px; }} tr.new td:first-child {{ border-left:4px solid var(--anofg); }}
</style></head><body>
<p><a href="index.html">Back to the coded interviews</a></p>
<h1>Anomalies and candidate inductive codes</h1>
<p>An anomaly is something that mattered in an interview but that no code in the codebook fits. The codebook was built from past research, so anomalies show where that research, as captured by the codebook, falls short.</p>
<h2>Candidate inductive codes ({m})</h2>
<p>The {n} anomalies grouped into candidate codes. For each, the codes drafted from the papers that state the same idea but were not kept among the core codes. A candidate with none (red edge) is not among the drafted codes: it may be new to this literature. Grouped by Claude in a Claude Code session, for the researchers to review.</p>
<div class="wrap"><table><tr><th>Candidate code</th><th>What it covers</th><th>Anomalies</th><th>In past research? (drafted codes)</th><th>Suggestion</th></tr>{trows}</table></div>
<h2>All anomalies ({n})</h2>
<div class="wrap"><table><tr><th>No.</th><th>Code</th><th>Interview and story</th><th>Label and why no code fits</th><th>Segments</th></tr>{arows}</table></div>
</body></html>
"""

if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]))
