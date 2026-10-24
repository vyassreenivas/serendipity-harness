"""Write the codebook trail: one page that shows how the codebook was built from the papers.

Usage: python trail.py codebook_review.xlsx codebook_trail.html

Two views of the same records:
  By sub-question  sub-question > analysis group > core code > the paper
                   sentences that state the code, with counts of candidate,
                   drafted and core codes at each level
  By paper         each paper and, under each sub-question, its sentences and
                   the codes they support
Only sentences chosen by reading count as evidence. A paper that reading found
does not state a code is left out of that code, and a code with no such
sentence is left out of the codebook. Holds codes, our wording and
one-sentence quotes from the papers; no interview text.
"""
import hashlib
import html
import sys
from collections import defaultdict
from datetime import date

from export import ADDED, DEFINITIONS, GROUPS, MISFIT as ANOMALY
from workbook import SQTEXT, cite as source, evidence_for, load_draft, state_from_workbook

MAPPED = defaultdict(int)  # candidates from the papers read later, merged into an existing code
for m in ADDED.get("maps", []):
    MAPPED[m["code"]] += 1


def candidates(code: dict) -> int:
    """Candidate codes merged into this drafted code."""
    return len(code.get("candidate_ids", [])) + MAPPED[code["id"]] + ("candidate_ids" not in code)

E = html.escape


def cite(e):
    link = f'<a href="{E(e["url"])}" target="_blank" rel="noopener">{E(e["short"])}</a>' if e["url"] else E(e["short"])
    page = f', p. {e["quote"]["pdf_page"]}' if e["quote"].get("pdf_page") else ""
    return link + page + f': <q>{E(e["quote"]["text"])}</q>'


def definitions(state, papers, by_paper, sq_papers, sq, key) -> str:
    """The definitions of serendipity, each worked out from the codes it needs, with the papers that state it."""
    blocks = []
    for d in DEFINITIONS:
        ev = []
        for q in d["evidence"]:
            e = dict(source(q["passage_id"].split(":")[0]), quote=q)
            ev.append(e)
            papers.setdefault(key(e), e)
            sq_papers.add(key(e))
            by_paper[key(e)][sq].append((f"Definition: {d['name']}", e))
        needs = " + ".join(f"<b>{E(state[cid]['Label'])}</b>" + ("" if part.lower() in state[cid]["Label"].lower() else f" ({E(part)})")
                         for cid, part in d["needs"])
        blocks.append(f'<details class="code"><summary><b>{E(d["name"])}</b><span class="when">{E(d["in_short"])}: met when {needs} are all coded.</span>'
                      f'<span class="n">{len({e["short"] for e in ev})} works</span></summary><ol>{"".join(f"<li>{cite(e)}</li>" for e in ev)}</ol></details>')
    return ('<h3>Definitions <span>Which definitions does the episode meet?</span></h3>'
            '<p class="flow">Not ticked by coders: worked out from the codes above and below.</p>' + "".join(blocks))


def build(xlsx: str, out: str) -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    papers, by_paper = {}, defaultdict(lambda: defaultdict(list))  # paper -> sq -> [(code label, evidence)]
    dropped = 0
    sq_order = [sq for sq in dict.fromkeys(sq for _, sq, _ in GROUPS) if sq != "all"]
    groups_by_sq = defaultdict(list)
    for name, sq, asks in GROUPS:
        if sq != "all":
            groups_by_sq[sq].append((name, asks))

    def key(e):
        return e["short"] + e["url"]

    sections, totals = [], defaultdict(int)
    for sq in sq_order:
        sq_papers, sq_counts, body = set(), defaultdict(int), []
        for name, asks in groups_by_sq[sq]:
            ids = sorted((i for i in draft if draft[i]["group"] == name), key=lambda i: int(i.split("-")[1]))
            cands = sum(candidates(draft[i]) for i in ids)
            rows = []
            for cid in ids:
                if state[cid]["Status"] != "core":
                    continue
                ev = evidence_for(draft[cid])
                dropped += sum(1 for e in ev if e.get("none"))
                ev = [e for e in ev if e["chosen"] and not e.get("none")]
                if not ev:
                    continue  # no sentence states it: not in the codebook
                s = state[cid]
                for e in ev:
                    papers.setdefault(key(e), e)
                    sq_papers.add(key(e))
                    by_paper[key(e)][sq].append((s["Label"], e))
                rows.append(
                    f'<details class="code"><summary><b>{E(s["Label"])}</b>'
                    f'<span class="when">{E(s["Code it when"])}</span>'
                    f'<span class="n">{len(ev)} paper{"s" * (len(ev) != 1)}</span></summary>'
                    f'<ol>{"".join(f"<li>{cite(e)}</li>" for e in ev)}</ol></details>')
            sq_counts["cands"] += cands
            sq_counts["drafted"] += len(ids)
            sq_counts["core"] += len(rows)
            body.append(f'<h3>{E(name.capitalize())} <span>{E(asks)}</span></h3>'
                        f'<p class="flow">{cands} candidate codes → {len(ids)} drafted → {len(rows)} core</p>' + "".join(rows))
            if name == "definition":
                body.append(definitions(state, papers, by_paper, sq_papers, sq, key))
        for k, v in sq_counts.items():
            totals[k] += v
        chips = ", ".join(f'<a href="#p{hashlib.sha1(k.encode()).hexdigest()[:8]}" class="chip">{E(papers[k]["short"])}</a>'
                          for k in sorted(sq_papers, key=lambda k: papers[k]["short"].lower()))
        sections.append(
            f'<section><h2>{sq} <span>{E(SQTEXT[sq])}</span></h2>'
            f'<p class="flow">{len(sq_papers)} papers · {sq_counts["cands"]} candidate codes → '
            f'{sq_counts["drafted"]} drafted → {sq_counts["core"]} core</p>' + "".join(body) +
            f'<p class="papers">Papers: {chips}</p></section>')

    paper_html = []
    for k in sorted(papers, key=lambda k: (-sum(len(v) for v in by_paper[k].values()), papers[k]["short"].lower())):
        e, n = papers[k], sum(len(v) for v in by_paper[k].values())
        parts = []
        for sq in sq_order:
            if by_paper[k][sq]:
                items = "".join(f'<li><q>{E(ev["quote"]["text"])}</q> <span class="p">p. {ev["quote"].get("pdf_page", "")}</span>'
                                f' → <b>{E(label)}</b></li>' for label, ev in by_paper[k][sq])
                parts.append(f'<h4>{sq} {E(SQTEXT[sq])}</h4><ul>{items}</ul>')
        title = E(e["title"]) + (f", <i>{E(e['venue'])}</i>" if e.get("venue") else "")
        paper_html.append(f'<details class="code" id="p{hashlib.sha1(k.encode()).hexdigest()[:8]}"><summary><b>{E(e["short"])}</b>'
                          f'<span class="when">{title}</span><span class="n">{n} code{"s" * (n != 1)}</span></summary>'
                          + (f'<p class="flow"><a href="{E(e["url"])}" target="_blank" rel="noopener">{E(e["url"])}</a></p>' if e["url"] else "")
                          + "".join(parts) + "</details>")

    anomaly = "".join(f'<tr><td>{E(m["id"])}</td><td>{E(m["label"])}</td><td>{E(m["applies_when"])}</td></tr>'
                      for m in ANOMALY["codes"])
    steps = [
        ("1", "Question", f"1 research question, {len(sq_order)} sub-questions, {sum(len(v) for v in groups_by_sq.values())} analysis groups", "Researchers"),
        ("2", "Papers", "113 papers and chapters read, each cut into numbered passages", "Researchers choose; fixed code cuts"),
        ("3", "Candidate codes", f"1,893 proposed, each citing the passages it rests on; {totals['cands']:,} merged into {totals['drafted']} drafts", "Model; fixed code checks every citation"),
        ("4", "Codebook", f"{totals['core']} core codes, each stated in at least one paper sentence; {len(DEFINITIONS)} definitions worked out from them; {len(ANOMALY['codes'])} anomaly codes", "Researchers"),
    ]
    strip = "".join(f'<div class="step"><div class="num">{n}</div><b>{t}</b><p>{d}</p><span>{w}</span></div>' for n, t, d, w in steps)
    page = PAGE.format(strip=strip, sections="".join(sections), papers="".join(paper_html), npapers=len(papers),
                       anomaly=anomaly, dropped=dropped, built=date.today().isoformat())
    open(out, "w", encoding="utf-8").write(page)
    print(f"wrote {out}: {totals['core']} core codes, {len(papers)} papers, {dropped} code-paper pairs dropped")


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
.strip{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}}
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
a{{color:var(--navy)}} .papers{{font-size:13px;color:var(--soft)}} .chip{{white-space:nowrap}}
table{{border-collapse:collapse;width:100%;font-size:14px}} td{{border-top:1px solid var(--line);padding:6px 8px;vertical-align:top}}
td:first-child{{white-space:nowrap;color:var(--soft)}}
footer{{font-size:12.5px;color:var(--soft);margin-top:30px;border-top:1px solid var(--line);padding-top:10px}}
[hidden]{{display:none}}
@media (max-width:700px){{.strip{{grid-template-columns:1fr 1fr}} summary{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>How the codebook was built</h1>
<p class="lead">Every code comes from the papers. Open a code to read the sentences that state it.</p>
<div class="strip">{strip}</div>
<p class="rule">A code is kept only if a paper states it in a sentence. Where a paper does not, it is left out of that code ({dropped} code-paper pairs).</p>
<div class="tabs"><button class="on" data-v="sq">By sub-question</button><button data-v="paper">By paper ({npapers})</button><button data-v="ano">When no code fits</button></div>
<div id="sq">{sections}</div>
<div id="paper" hidden><p class="flow">Each paper, what it says under each sub-question, and the code each sentence supports.</p>{papers}</div>
<div id="ano" hidden><p class="flow">Anomaly codes hold what no core code captures. They have no paper evidence by design: they mark where the literature may be silent.</p><table>{anomaly}</table></div>
<footer>Page numbers are PDF pages. Drafted codes not kept as core stay in the review workbook (codebook_review.xlsx) with their reasons. Built {built}.</footer>
</main><script>
const show=v=>{{for(const id of["sq","paper","ano"])document.getElementById(id).hidden=id!==v;
document.querySelectorAll(".tabs button").forEach(b=>b.classList.toggle("on",b.dataset.v===v))}};
document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>show(b.dataset.v));
document.querySelectorAll("a.chip").forEach(a=>a.onclick=ev=>{{ev.preventDefault();show("paper");
const d=document.querySelector(a.getAttribute("href"));d.open=true;d.scrollIntoView({{block:"start"}})}});
</script></body></html>
"""

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
