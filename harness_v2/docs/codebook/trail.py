"""Write the codebook trail: one page that shows how the codebook was built from the papers.

Usage: python trail.py codebook_review.xlsx codebook_trail.html

Three views of the same records:
  By sub-question  sub-question > group > level-1 code > the paper sentences
                   that state it, with counts of candidate, drafted and kept codes
  Worked out       the level-2 definitions, rival explanations, types and
                   judgments, each with its rule and the papers behind it
  By paper         each paper, what it says under each sub-question, and the code
                   each sentence supports
Only sentences chosen by reading count as evidence. A paper that does not state a
code is left out of that code, and a code no paper states is left out of the
codebook. Holds codes, our wording and one-sentence quotes from the papers; no
interview text.
"""
import hashlib
import json
import html
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from export import ADDED, LEVELS, MISFIT as ANOMALY
from levels import CORE_PAPERS, SUB_QUESTIONS, level1, numbers, rule_equation, rule_evidence
from workbook import evidence_for, load_draft, state_from_workbook

# Counts of the works read, from the paper list (paper_list.py runs first).
READ = json.loads(Path(__file__).with_name("paper_list.json").read_text(encoding="utf-8"))
MAPPED = defaultdict(int)  # candidates from the papers read later, merged into an existing code
for m in ADDED.get("maps", []):
    MAPPED[m["code"]] += 1
KINDS = [("definition", "Definitions of serendipity"), ("rival", "Rival explanations"),
         ("type", "Type"), ("judgment", "Decided by the researchers")]
E = html.escape


def candidates(code: dict) -> int:
    """Candidate codes merged into this drafted code."""
    return len(code.get("candidate_ids", [])) + MAPPED[code["id"]] + ("candidate_ids" not in code)


def cite(e):
    link = f'<a href="{E(e["url"])}" target="_blank" rel="noopener">{E(e["short"])}</a>' if e["url"] else E(e["short"])
    page = f', p. {e["quote"]["pdf_page"]}' if e["quote"].get("pdf_page") else ""
    tags = [t for t, on in (("found on the second check", e.get("recheck")), ("leans on the code", e.get("close"))) if on]
    return link + page + f': <q>{E(e["quote"]["text"])}</q>' + (f' <span class="p">({"; ".join(tags)})</span>' if tags else "")


def item(name, when, ev, unconfirmed=()):
    n = len({e["short"] for e in ev})
    checked = (f'<p class="p">Also cited for this code, but no sentence confirmed it on either check: '
               f'{E("; ".join(dict.fromkeys(e["short"] + (" (text not readable)" if e.get("recheck") == "not readable" else "") for e in unconfirmed)))}.</p>'
               if unconfirmed else "")
    return (f'<details class="code"><summary><b>{E(name)}</b><span class="when">{when}</span>'
            f'<span class="n">{n} work{"s" * (n != 1)}</span></summary>'
            f'<ol>{"".join(f"<li>{cite(e)}</li>" for e in ev)}</ol>{checked}</details>')


def split(entries):
    """Links a sentence confirmed, and links checked twice without one."""
    return ([e for e in entries if e["chosen"] and not e.get("none")], [e for e in entries if e.get("none")])


def anchor(k):
    return "p" + hashlib.sha1(k.encode()).hexdigest()[:8]


def build(xlsx: str, out: str) -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    label = {c: state[c]["Label"] for c in draft}
    num = numbers(state, draft)
    papers, by_paper = {}, defaultdict(lambda: defaultdict(list))  # paper -> section -> [(what it supports, evidence)]
    links = [e for c in draft if state[c]["Status"] == "core" for e in evidence_for(draft[c])]
    first = sum(1 for e in links if e["chosen"] and not e.get("none") and not e.get("recheck"))
    second = sum(1 for e in links if e.get("recheck") in ("states it", "leans on it"))
    unconfirmed = sum(1 for e in links if e.get("none"))
    groups = level1(state, draft)
    sq_order = list(dict.fromkeys(g["sq"] for g in groups))
    in_level1 = set()

    def keep(ev, section, what):
        for e in ev:
            k = e["short"] + e["url"]
            papers.setdefault(k, e)
            by_paper[k][section].append((what, e))
        return {e["short"] + e["url"] for e in ev}

    sections = []
    for sq in sq_order:
        sq_papers, body = set(), []
        for g in [g for g in groups if g["sq"] == sq]:
            drafted = [i for i in draft if draft[i]["group"] in ({"definition", "type"} if g["group"] == "parts" else {g["group"]})]
            ids = (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]
            in_level1 |= set(ids)
            rows = []
            if g["pick_one"]:
                rows.append(f'<p class="flow"><b>{E(g["pick_one"]["name"])}</b> (pick one): {E(g["pick_one"]["asks"])}</p>')
            for i, cid in enumerate(ids):
                if g["pick_one"] and i == len(g["pick_one"]["codes"]):
                    rows.append('<p class="flow"><b>Then tick each part present</b></p>')
                ev, nc = split(evidence_for(draft[cid]))
                sq_papers |= keep(ev, sq, f"{num[cid]} {label[cid]}")
                rows.append(item(f"{num[cid]} {label[cid]}", E(state[cid]["Code it when"]), ev, nc))
            body.append(f'<h3>{E(g["name"])} <span>{E(g["asks"])}</span></h3>'
                        f'<p class="flow">{sum(candidates(draft[i]) for i in drafted)} candidate codes → {len(drafted)} drafted → '
                        f'{len(ids)} for coders</p>' + "".join(rows))
        chips = ", ".join(f'<a href="#{anchor(k)}" class="chip">{E(papers[k]["short"])}</a>'
                          for k in sorted(sq_papers, key=lambda k: papers[k]["short"].lower()))
        sections.append(f'<section><h2>{sq} <span>{E(SUB_QUESTIONS[sq])}</span></h2>' + "".join(body) +
                        f'<p class="papers">Papers: {chips}</p></section>')

    level2 = []
    for kind, title in KINDS:
        rows = []
        for k2, r in enumerate([r for r in LEVELS["level2"] if r["kind"] == kind], 1):
            no = {"definition": "D", "rival": "R", "type": "T", "judgment": "J"}[kind] + str(k2)
            ev = rule_evidence(r, draft)
            nc = [e for c in r.get("evidence_from", []) for e in evidence_for(draft[c]) if e.get("none")]
            keep(ev, "L2", f"{no} {r['name']}")
            when = (f"{E(r['in_short'])}. Met when: <b>{E(rule_equation(r, label, num))}</b>." if kind != "judgment"
                    else f"{E(r['in_short'])}. The researchers decide, with a written reason.")
            rows.append(item(f"{no} {r['name']}", when, ev, nc))
        level2.append(f'<h3>{E(title)}</h3>' + "".join(rows))

    names = dict(SUB_QUESTIONS, L2="Worked out after coding (level 2)")
    paper_html = []
    for k in sorted(papers, key=lambda k: (-sum(len(v) for v in by_paper[k].values()), papers[k]["short"].lower())):
        e, n = papers[k], sum(len(v) for v in by_paper[k].values())
        parts = []
        for sec in sq_order + ["L2"]:
            if by_paper[k][sec]:
                items = "".join(f'<li><q>{E(ev["quote"]["text"])}</q> <span class="p">p. {ev["quote"].get("pdf_page", "")}</span>'
                                f' → <b>{E(what)}</b></li>' for what, ev in by_paper[k][sec])
                parts.append(f'<h4>{"" if sec == "L2" else sec + " "}{E(names[sec])}</h4><ul>{items}</ul>')
        title = E(e["title"]) + (f", <i>{E(e['venue'])}</i>" if e.get("venue") else "")
        core = ' <span class="core">core paper</span>' if e["short"] in CORE_PAPERS else ""
        paper_html.append(f'<details class="code" id="{anchor(k)}"><summary><b>{E(e["short"])}</b>{core}'
                          f'<span class="when">{title}</span><span class="n">{n} code{"s" * (n != 1)}</span></summary>'
                          + (f'<p class="flow"><a href="{E(e["url"])}" target="_blank" rel="noopener">{E(e["url"])}</a></p>' if e["url"] else "")
                          + "".join(parts) + "</details>")

    anomaly = "".join(f'<tr><td>{E(m["id"])}</td><td>{E(m["label"])}</td><td>{E(m["applies_when"])}</td></tr>'
                      for m in ANOMALY["codes"] if m["id"] not in ("ANO-TYP", "ANO-RIV"))
    n_anomaly = anomaly.count("<tr>")
    cands = sum(candidates(c) for c in draft.values())
    steps = [
        ("1", "Question", f"1 research question, {len(sq_order)} sub-questions, {len(groups)} groups coders answer", "Researchers"),
        ("2", "Papers", f"{READ['works']} works read ({READ['read']} files, the chapters of one book counted once); "
         f"{len(papers)} state a code; the {len(CORE_PAPERS)} core papers state every code", "We choose them; a program splits each into numbered passages"),
        ("3", "Candidate codes", f"1,893 proposed, each citing the passages it rests on; {cands:,} merged into {len(draft)} drafts", "The model proposes; a program checks every citation"),
        ("4", "Checking every link", f"{first + second + unconfirmed} code-paper links: {first} confirmed by a cited sentence, "
         f"{second} more on a second check of the whole paper, {unconfirmed} not confirmed and shown as such", "We read; a program searches each paper"),
        ("5", "Codebook 1.0", f"{len(in_level1)} codes coders tick and {len(LEVELS['level2'])} worked out after coding, each stated in a paper sentence; {n_anomaly} anomaly codes", "Researchers"),
    ]
    strip = "".join(f'<div class="step"><div class="num">{n}</div><b>{t}</b><p>{d}</p><span>{w}</span></div>' for n, t, d, w in steps)
    page = PAGE.format(strip=strip, sections="".join(sections), level2="".join(level2), papers="".join(paper_html),
                       npapers=len(papers), anomaly=anomaly, built=date.today().isoformat())
    open(out, "w", encoding="utf-8").write(page)
    print(f"wrote {out}: {len(in_level1)} level-1 codes, {len(LEVELS['level2'])} level-2 items, {len(papers)} papers, "
          f"links: {first} confirmed, {second} on second check, {unconfirmed} not confirmed")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Codebook trail</title>
<style>
:root{{--ink:#1a1a1a;--soft:#5a5a5a;--line:#dcdcdc;--bg:#fff;--tint:#f5f6f8;--navy:#1f3a5f;--green:#d7ebd5;--orange:#fbe3c4}}
@media (prefers-color-scheme:dark){{:root{{--ink:#e8e8e8;--soft:#a8a8a8;--line:#3a3a3a;--bg:#16181c;--tint:#20242a;--navy:#8fb3e0;--green:#2c4a2a;--orange:#5a4020}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:980px;margin:0 auto;padding:24px 16px 60px}}
h1{{font-size:24px;margin:0 0 4px;color:var(--navy)}}
.lead{{color:var(--soft);margin:0 0 18px}}
.strip{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:18px}}
.step{{background:var(--tint);border-radius:8px;padding:10px 12px;position:relative}}
.step .num{{font-size:12px;color:var(--soft)}} .step p{{margin:4px 0;font-size:13.5px}} .step span{{font-size:12px;color:var(--soft);font-style:italic}}
.rule{{border-left:3px solid var(--navy);padding:6px 12px;margin:0 0 18px;background:var(--tint)}}
.tabs{{display:flex;gap:6px;margin:6px 0 14px;border-bottom:1px solid var(--line)}}
.tabs button{{font:inherit;border:0;background:none;padding:8px 12px;cursor:pointer;color:var(--soft);border-bottom:2px solid transparent}}
.tabs button.on{{color:var(--ink);border-color:var(--navy);font-weight:600}}
section{{margin:0 0 26px}}
h2{{font-size:19px;margin:18px 0 2px;color:var(--navy)}} h2 span,h3 span{{font-weight:400;color:var(--ink)}}
h3{{font-size:15.5px;margin:14px 0 2px}} h4{{font-size:13.5px;margin:10px 0 4px;color:var(--soft)}}
.flow{{font-size:13px;color:var(--soft);margin:0 0 6px}}
details.code{{border:1px solid var(--line);border-radius:6px;margin:4px 0;padding:0 10px}}
details.code[open]{{background:var(--tint)}}
summary{{cursor:pointer;padding:7px 0;display:grid;grid-template-columns:minmax(150px,230px) 1fr auto;gap:12px;align-items:baseline}}
summary .when{{color:var(--soft);font-size:13.5px}} summary .n{{font-size:12.5px;color:var(--soft);white-space:nowrap}}
ol,ul{{margin:4px 0 10px;padding-left:22px}} li{{margin:5px 0;font-size:14px}}
q{{quotes:"\\201C" "\\201D"}} .p{{color:var(--soft);font-size:12.5px}}
a{{color:var(--navy)}} .papers{{font-size:13px;color:var(--soft)}} .chip{{white-space:nowrap}} .core{{font-size:11px;color:var(--navy);border:1px solid var(--navy);border-radius:8px;padding:0 6px;margin-left:4px}}
table{{border-collapse:collapse;width:100%;font-size:14px}} td{{border-top:1px solid var(--line);padding:6px 8px;vertical-align:top}}
td:first-child{{white-space:nowrap;color:var(--soft)}}
footer{{font-size:12.5px;color:var(--soft);margin-top:30px;border-top:1px solid var(--line);padding-top:10px}}
[hidden]{{display:none}}
@media (max-width:700px){{.strip{{grid-template-columns:1fr 1fr}} summary{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>How the codebook was built</h1>
<p class="lead">Codebook version 1.0. Coders tick level-1 codes; level-2 codes are worked out from them after coding. Every code at both levels comes from the papers: open one to read the sentences that state it.</p>
<div class="strip">{strip}</div>
<div class="tabs"><button class="on" data-v="sq">Level 1, by sub-question</button><button data-v="l2">Level 2, worked out</button><button data-v="paper">By paper ({npapers})</button><button data-v="ano">When no code fits</button></div>
<div id="sq">{sections}</div>
<div id="l2" hidden><p class="flow">Not ticked by coders. A rule is met when the codes it names are ticked, and "without" means a code is not ticked.</p>{level2}</div>
<div id="paper" hidden><p class="flow">Each paper, what it says under each sub-question, and the code each sentence supports.</p>{papers}</div>
<div id="ano" hidden><p class="flow">Anomaly codes hold what no core code captures. They have no paper evidence by design: they mark where the literature may be silent.</p><table>{anomaly}</table></div>
<footer>Page numbers are PDF pages. Drafted codes not kept as core stay in the review workbook (codebook_review.xlsx) with their reasons. Built {built}.</footer>
</main><script>
const show=v=>{{for(const id of["sq","l2","paper","ano"])document.getElementById(id).hidden=id!==v;
document.querySelectorAll(".tabs button").forEach(b=>b.classList.toggle("on",b.dataset.v===v))}};
document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>show(b.dataset.v));
document.querySelectorAll("a.chip").forEach(a=>a.onclick=ev=>{{ev.preventDefault();show("paper");
const d=document.querySelector(a.getAttribute("href"));d.open=true;d.scrollIntoView({{block:"start"}})}});
</script></body></html>
"""

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
