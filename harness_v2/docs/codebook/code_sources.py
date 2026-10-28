"""Write a simple table of every code with the papers it came from and their quotes.

Usage: python code_sources.py codebook_review.xlsx code_sources.html

One row per code: its group, its number and label, and each paper that states it
with the sentence chosen by reading (and its page). Level-2 items follow, each
with its rule. A link that only comes close is marked "leans on it". Holds codes,
our wording and one-sentence quotes from the papers; no interview text.
"""
import html
import sys
from datetime import date

from export import LEVELS
from levels import CORE_PAPERS, SUB_QUESTIONS, level1, numbers, rule_equation, rule_evidence
from workbook import evidence_for, load_draft, state_from_workbook

E = html.escape
KINDS = [("definition", "Definitions", "D"), ("rival", "Rival explanations", "R"),
         ("type", "Types", "T"), ("judgment", "Decided by the researchers", "J")]


def sources(ev: list[dict]) -> str:
    ev = sorted(ev, key=lambda e: e["short"] not in CORE_PAPERS)  # core papers first
    items = []
    for e in ev:
        q = e.get("quote") or {}
        page = f", p. {q['pdf_page']}" if q.get("pdf_page") else ""
        lean = ' <span class="lean">leans on it</span>' if e.get("close") else ""
        lean += ' <span class="core">core paper</span>' if e["short"] in CORE_PAPERS else ""
        quote = f'<q>{E(q["text"])}</q>' if q.get("text") else '<span class="none">no quote held</span>'
        items.append(f'<li><b>{E(e["short"])}</b>{page}{lean}<br>{quote}</li>')
    return f'<ul>{"".join(items)}</ul>' if items else '<span class="none">none</span>'


def build(xlsx: str, out: str) -> None:
    state, draft = state_from_workbook(xlsx), load_draft()
    num = numbers(state, draft)
    label = {c: state[c]["Label"] for c in draft}
    rows, n_codes = [], 0
    for gi, g in enumerate(level1(state, draft), 1):
        ids = (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]
        for k, c in enumerate(ids):
            ev = [e for e in evidence_for(draft[c]) if e["chosen"] and not e.get("none")]
            group = (f'<td rowspan="{len(ids)}" class="group"><b>{gi}. {E(g["name"])}</b><br>'
                     f'<span>{g["sq"]}: {E(SUB_QUESTIONS[g["sq"]])}</span></td>') if k == 0 else ""
            rows.append(f'<tr>{group}<td class="code"><span class="no">{num[c]}</span> {E(label[c])}</td>'
                        f'<td>{sources(ev)}</td></tr>')
            n_codes += 1
    level2 = []
    for kind, title, letter in KINDS:
        items = [r for r in LEVELS["level2"] if r["kind"] == kind]
        for k, r in enumerate(items, 1):
            rule = rule_equation(r, label, num) if kind != "judgment" else "Decided by the researchers, with a written reason"
            group = f'<td rowspan="{len(items)}" class="group"><b>{E(title)}</b></td>' if k == 1 else ""
            level2.append(f'<tr>{group}<td class="code"><span class="no">{letter}{k}</span> {E(r["name"])}'
                          f'<div class="rule">{E(rule)}</div></td><td>{sources(rule_evidence(r, draft))}</td></tr>')
    page = PAGE.format(built=date.today().isoformat(), n=n_codes, rows="".join(rows),
                       n2=len(LEVELS["level2"]), level2="".join(level2))
    open(out, "w", encoding="utf-8").write(page)
    print(f"wrote {out}: {n_codes} level-1 codes, {len(LEVELS['level2'])} level-2 items")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codebook sources</title>
<style>
:root {{ --bg:#fff; --fg:#1d2329; --muted:#5d6670; --line:#d5dbe1; --head:#1f3a5f; --tint:#eef2f6; --lean:#8a5a00; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42; --head:#2c4f7a; --tint:#1c232b; --lean:#e0b060; }} }}
:root[data-theme="dark"] {{ --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42; --head:#2c4f7a; --tint:#1c232b; --lean:#e0b060; }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, -apple-system, Segoe UI, sans-serif; margin:0; padding:24px 16px; }}
main {{ max-width:1100px; margin:0 auto; }}
h1 {{ font-size:24px; margin:0 0 4px; }} h2 {{ font-size:19px; margin:32px 0 8px; }}
p.meta {{ color:var(--muted); margin:0 0 16px; }}
.wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; min-width:640px; }}
th {{ background:var(--head); color:#fff; text-align:left; padding:8px 10px; position:sticky; top:0; }}
td {{ border:1px solid var(--line); padding:8px 10px; vertical-align:top; }}
td.group {{ background:var(--tint); width:18%; }} td.group span {{ color:var(--muted); font-size:13px; }}
td.code {{ width:22%; font-weight:600; }} .no {{ color:var(--muted); font-weight:400; margin-right:4px; }}
.rule {{ font-weight:400; color:var(--muted); font-size:13px; margin-top:4px; }}
ul {{ margin:0; padding-left:18px; }} li {{ margin-bottom:6px; }}
q {{ font-style:italic; }} .core {{ font-size:11px; color:var(--head); border:1px solid var(--head); border-radius:8px; padding:0 6px; margin-left:4px; }} .lean {{ color:var(--lean); font-size:12px; margin-left:4px; }} .none {{ color:var(--muted); }}
</style></head><body><main>
<h1>Codebook sources</h1>
<p class="meta">Codebook version 1.0. Each code with the papers that state it and the sentence from each, with its page. Papers in the core list come first and are tagged. Built {built}.</p>
<h2>Level 1: what coders tick ({n} codes)</h2>
<div class="wrap"><table><thead><tr><th>Group</th><th>Code</th><th>Papers and quotes</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Level 2: worked out from level-1 codes ({n2} items)</h2>
<div class="wrap"><table><thead><tr><th>Kind</th><th>Item and rule</th><th>Papers and quotes</th></tr></thead><tbody>{level2}</tbody></table></div>
</main></body></html>
"""

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
