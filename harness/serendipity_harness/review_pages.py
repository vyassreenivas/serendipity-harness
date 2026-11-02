"""Write the reviewer pages: each step of the chain as one plain page.

Usage: python -m serendipity_harness.review_pages OUT_DIR

The chain, in reading order:
  1_codebook_v1.html      codebook version 1.0, built from papers only
  2_round1_coding.html    the first 25 interviews coded with version 1.0
  3_paper_search.html     each round-1 anomaly checked against the papers, and
                          where it went
  4_codebook_v2.html      version 2.0: version 1.0 plus the codes the anomalies
                          earned, with the passages they took over
  5_progression.html      one table: each version, its round, where the
                          anomalies went and reliability
  6_round2_coding.html    round 2: new interviews and round 1's coded again, with
                          reliability code by code
  7_codebook_v3.html      version 3.0: version 2.0 plus the codes round 2 earned
  8_round3_coding.html    round 3, the last calibration round: new interviews and
                          rounds 1 and 2's coded again with version 3.0, the
                          anomaly themes, and reliability for each earlier round
Round pages read the redacted coding in harness_v2/outputs/review_confidential
(serendipity_harness.redact), so interviews appear as "Interview 01".
index.html links them in order. A codebook page runs from the research
question to its groups and codes; each code folds away the sentence from each
paper that states it (evidence_v<version>.json), and the papers are listed with
the codes they state.

Reads harness/codebook (codebook versions, changes, evidence, anomaly log, paper
details, sub-questions in harness_v2/docs/codebook/questions.json) and the checked coding of round 1. Holds codes, our wording, short
quotes from papers, and the coders' short labels and reasons; no interview
text. Run the submission's privacy check on OUT_DIR before sharing it.
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

from .model_coding import codebook_from
from .runlog import ROOT

E = html.escape
PAPERS: dict = {}  # references for papers not in paper_metadata.json, from the evidence files
CB = ROOT / "harness" / "codebook"
# The document tools: harness_v2/ in our working files, documents/ in the submission repository.
DOCS = ROOT / "harness_v2" if (ROOT / "harness_v2").exists() else ROOT / "documents"
ID = re.compile(r"\b(?:definition|type|trigger|mechanism|background|role|outcome|account|rival|condition)-\d+\b")
ANO = re.compile(r"\b(?:use |code )?ANO-[A-Z]{3}\b")


def load(name: str) -> dict:
    return json.loads((CB / name).read_text(encoding="utf-8"))


def numbering(cb: dict) -> dict:
    num = {}
    for gi, g in enumerate(cb["groups"], 1):
        for k, c in enumerate((g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"], 1):
            num[c] = f"{gi}.{k}"
        if g["anomaly"]:
            num[g["anomaly"]["id"]] = f"{gi}.A"
    return num


def cite(pid: str, meta: dict, files: dict) -> str:
    """Author (year) Title, from the paper details, else from the reading copy's file name."""
    m = meta.get(pid)
    if m:
        a = m.get("authors") or [m["file_author"]]
        who = a[0] if len(a) == 1 else f"{a[0]} and {a[1]}" if len(a) == 2 else f"{a[0]} et al."
        title = m.get("title") or m.get("file_title", pid)
        doi = f' <a href="https://doi.org/{E(m["doi"])}">doi</a>' if m.get("doi") else ""
        return f"{E(who)} ({m.get('year') or m.get('file_year', '')}). <i>{E(title)}</i>.{doi}"
    if pid in files:
        who, year, title = (Path(files[pid]).stem.split(" - ", 2) + ["", ""])[:3]
        return f"{E(who.replace(' et al', ' et al.'))} ({E(year)}). <i>{E(title)}</i>."
    return E(pid)


def plain(text: str, labels: dict) -> str:
    """Code ids in older wording become their labels; anomaly ids become words."""
    text = ID.sub(lambda m: f"“{labels.get(m.group(0), m.group(0))}”", text)
    text = ANO.sub("the group's anomaly code", text)
    return E(text).replace("\n", "<br>")


def page(title: str, intro: str, body: str) -> str:
    return PAGE.format(title=E(title), intro=intro, body=body)


EXAMPLE = re.compile(r"\s*For example(?: \(([^)]*)\))?:\s*(.*)$", re.S)
# Each group's question in plain words, for the overview table; the codebook's own wording is under each group.
PLAIN = {"parts": "Was it serendipity: surprising, acted on, valuable? What was the founder doing at the time?",
         "trigger": "What unexpected thing set it off?",
         "background": "What did the founder already have that helped?",
         "mechanism": "What did the founder do with it?",
         "role": "What did it do for the venture?",
         "outcome": "What came of it?",
         "condition": "What made it more or less likely?",
         "account": "How does the founder explain it afterwards?"}
KINDS = [("definition", "Definitions", "Which definition of serendipity does the story meet?"),
         ("rival", "Rival explanations", "Is it better explained as something else?"),
         ("type", "Types of serendipity", "Which kind of serendipity was it?"),
         ("judgment", "Decided by the researchers", "Judged from the whole account, with a written reason.")]


def short(e: dict, meta: dict, files: dict) -> str:
    """Author (year) for a paper sentence, from the entry, the paper details or the file name."""
    if e.get("short"):
        return e["short"]
    if e["paper"] in PAPERS:
        return PAPERS[e["paper"]]["short"]
    m = meta.get(e["paper"])
    if m:
        a = m.get("authors") or [m["file_author"]]
        who = a[0] if len(a) == 1 else f"{a[0]} and {a[1]}" if len(a) == 2 else f"{a[0]} et al."
        return f"{who} ({m.get('year') or m.get('file_year', '')})"
    who, year = (Path(files.get(e["paper"], e["paper"])).stem.split(" - ", 2) + [""])[:2]
    return f"{who.replace(' et al', ' et al.')} ({year})"


def url(e: dict, meta: dict) -> str:
    if e.get("url"):
        return e["url"]
    m = PAPERS.get(e["paper"]) or meta.get(e["paper"], {})
    return f"https://doi.org/{m['doi']}" if m.get("doi") else ""


def reference(e: dict, meta: dict, files: dict) -> str:
    """Author (year). Title., linked to the paper where it has a DOI."""
    title = e.get("title") or PAPERS.get(e["paper"], {}).get("title") or meta.get(e["paper"], {}).get("title") or \
        (Path(files.get(e["paper"], "")).stem.split(" - ", 2) + ["", "", ""])[2]
    link = url(e, meta)
    t = f'<a href="{E(link)}">{E(title)}</a>' if link else E(title)
    return f"{E(short(e, meta, files))}. <i>{t}</i>"


def quotes(items: list, meta: dict, files: dict, linked: list | None = None) -> str:
    """The papers that state a code, folded: author, page, sentence."""
    if not items:
        return '<p class="muted">No paper states it.</p>'
    li = "".join(f'<li>{reference(e, meta, files)}, {"PDF " if e.get("page_kind") == "pdf" else ""}'
                 f'p. {E(str(e["page"]))}{" <span class=lean>leans on it</span>" if e.get("leans") else ""}'
                 f'<br><q>{E(e["quote"])}</q></li>' for e in items)
    more = f'<p class="muted">Also linked, but no sentence states it: {E(", ".join(linked))}.</p>' if linked else ""
    return f'<details><summary>Papers that state it ({len(items)})</summary><ol>{li}</ol>{more}</details>'


def rule_text(r: dict, labels: dict, num: dict) -> str:
    part = lambda c: f"{num[c]} {labels[c]}"
    terms = [" + ".join(part(c) for c in r.get("all", []))] if r.get("all") else []
    if r.get("any"):
        terms.append("(" + " or ".join(part(c) for c in r["any"]) + ")")
    terms += [f"not {part(c)}" for c in r.get("none", [])]
    return " + ".join(terms) or "Read from the whole account"


def dont_lines(code: dict, version: str, changes: dict | None, new_labels: set, labels: dict) -> str:
    """The "don't use it when" lines, each tagged with where it came from: written with a code added or extended (now covering more)
    in this version; added to an older code to point to a new one; or carried over (version 1: the review)."""
    out = []
    for line in code["does_not_apply_when"].split("\n"):
        if version == "1.0":
            src = "from the review"
        elif changes and code["id"] in {e["id"] for e in changes["codes"]}:
            src = f"written with this code, version {version}"
        elif any(f'"{l}"' in line for l in new_labels):
            src = f"added in version {version}: points to a new code"
        elif changes and any(f'"{labels[o]}"' in line for k in changes.get("confused_pairs", {})
                             for o in k.split("|") if code["id"] in k.split("|") and o != code["id"] and o in labels):
            src = "kept: coders confused these in the last agreement check"
        else:
            src = "carried over from the version before"
        out.append(f'{plain(line, labels)} <span class="src">{src}</span>')
    return "<br>".join(out)


def codebook_page(cb: dict, version: str, meta: dict, files: dict, evidence: dict, changes: dict | None,
) -> tuple[int, str]:
    """One codebook version: what is new (from its changes file), question to groups, groups at a glance, every
    code, level 2, papers to codes."""
    view = codebook_from(cb)
    num, labels = numbering(view), view["labels"]
    added = {e["id"]: e for e in changes["codes"]} if changes else {}
    sq = json.loads((DOCS / "docs/codebook/questions.json").read_text(encoding="utf-8"))
    sq_text = {f"SQ{r['sq']}": r["text"] for r in sq["rows"]}
    groups = [dict(g, sq=l["sq"], no=gi) for gi, (g, l) in enumerate(zip(view["groups"], cb["levels"]["level1"]), 1)]
    ids = lambda g: (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]
    n = sum(len(ids(g)) for g in groups)
    ev = lambda c: evidence["codes"].get(c, [])
    papers, refs = {}, {}
    for g in groups:
        for c in ids(g):
            for e in ev(c):
                papers.setdefault(short(e, meta, files), []).append(c)
                refs.setdefault(short(e, meta, files), reference(e, meta, files))
    new_labels = {labels[c] for c in labels if view["codes"].get(c, {}).get("added_in") == version}
    tag = lambda c: ('<span class="tag new">new</span>' if view["codes"][c].get("added_in") == version
                     else '<span class="tag rev">now covers more</span>') if c in added else ""

    stats = (f'<div class="stats"><span><b>1</b> question</span><span><b>{len(sq_text) - 1}</b> sub-questions</span>'
             f'<span><b>{len(groups)}</b> groups</span><span><b>{n}</b> codes</span>'
             f'<span><b>{len(papers)}</b> papers</span></div>')
    toc = ('<nav class="toc">' + ('<a href="#version">What\'s new</a>' if changes else "") + '<a href="#map">Question and groups</a><a href="#glance">Groups at a glance</a>'
           + "".join(f'<a href="#g{g["no"]}">{g["no"]}. {E(g["title"])}</a>' for g in groups)
           + '<a href="#level2">Level 2</a><a href="#papers">Papers</a>'
           + ('<a href="#open">Open anomalies</a>' if changes else "") + "</nav>")

    # Level-2 items answer SQ1 (what counts as serendipity), except a judgment read from how the founder tells
    # it, which answers the sub-question of the account group (SQ6).
    sq_of = {l["group"]: l["sq"] for l in cb["levels"]["level1"]}
    level2_sq = []
    for kind, title, _ in KINDS:
        rs = [r for r in cb["levels"]["level2"] if r["kind"] == kind]
        if kind != "judgment":
            level2_sq.append({"id": kind, "name": f"{title} ({len(rs)})", "sq": "SQ1"})
        for r in rs if kind == "judgment" else []:
            src = view["codes"].get(r["evidence_from"][0], {}).get("group") or \
                next((c["group"] for c in cb["codes"] if c["id"] == r["evidence_from"][0]), "")
            level2_sq.append({"id": r["id"], "name": r["name"], "sq": sq_of.get(src, "SQ1")})
    rows = []
    for k in [f"SQ{i}" for i in range(1, len(sq_text))]:
        gs = [g for g in groups if g["sq"] == k]
        extra = [f'Level 2: <a href="#{x["id"]}">{E(x["name"])}</a>' for x in level2_sq if x["sq"] == k]
        rows.append(f'<tr><td>{k}</td><td>{E(sq_text[k])}</td><td>'
                    + "<br>".join([f'<a href="#g{g["no"]}">{g["no"]}. {E(g["title"])}</a>' for g in gs] + extra)
                    + f'</td><td>{sum(len(ids(g)) for g in gs)}</td></tr>')
    rows.append(f'<tr><td>All</td><td>{E(sq_text["SQAll"])}</td><td>An anomaly code in each group</td><td></td></tr>')
    about = ""
    if changes:
        group_of = {c: g for g in groups for c in ids(g)}
        ano_group = {g["anomaly"]["id"]: g for g in groups if g["anomaly"]}
        moved = sum(len(e.get("absorbs", [])) for e in changes["codes"])
        order = sorted(changes["codes"], key=lambda e: [int(x) for x in num[e["id"]].split(".")])
        new_rows = "".join(
            f'<tr><td>{E(group_of[e["id"]]["title"])}</td><td><a href="#{e["id"]}">{num[e["id"]]} '
            f'{E(labels[e["id"]])}</a></td><td>{"new" if view["codes"][e["id"]].get("added_in") == version else "existing code, now covers more" + (f' ({E(e["extends"]["was"])} → {E(e["extends"]["now"])})' if e.get("extends") else "")}'
            f'</td><td>{len(e.get("absorbs", []))}</td></tr>' for e in order)
        cites = lambda c: "; ".join(dict.fromkeys(short(x, meta, files) for x in ev(c)))
        ano_rows = "".join(
            f'<tr><td>{E(a["anomaly"])}</td><td>{E(a["comment"])}</td>'
            f'<td>{num.get(a["was"], "")} {E(ano_group[a["was"]]["title"]) + ": nothing fits" if a["was"] in ano_group else E(a["was"])}</td>'
            f'<td><a href="#{e["id"]}">{num[e["id"]]} {E(labels[e["id"]])}</a></td>'
            f'<td>{E(cites(e["id"]))} <a href="#{e["id"]}">quotes</a></td></tr>'
            for e in order for a in sorted(e.get("absorbs", []), key=lambda a: a["anomaly"]))
        rnd = int(float(changes["from"]))
        open_now = [a for a in changes["open_anomalies"] if a.get("round", 1) == rnd]
        earlier = len(changes["open_anomalies"]) - len(open_now)
        about = (f'<h2 id="version">What\'s new since version {changes["from"]}</h2>'
                 f'<p class="lead">Round {rnd} left <b>{moved + len(open_now)}</b> passages that no code '
                 f'fit. <b>{moved}</b> now have a code. <b>{len(open_now)}</b> <a href="#open">stay open</a>'
                 + (f', plus {earlier} still open from earlier rounds' if earlier else "") + '.</p>'
                 '<div class="wrap"><table><thead><tr><th>Group</th><th>Code</th>'
                 f'<th>Change</th><th>Round-{rnd} passages</th></tr></thead><tbody>{new_rows}</tbody></table></div>'
                 '<p class="muted">A code was added only if a paper read in full states it. '
                 + ('Every "Don\'t use it when" line now names the code to use instead.' if rnd == 1 else
                    'A "Don\'t use it when" line between two codes of a group stays only if coders confused them in the '
                    'last agreement check, or one of them is new.') + '</p>'
                 f'<h3>Each round-{rnd} anomaly that now has a code</h3><div class="wrap"><table><thead><tr><th>No.</th>'
                 f'<th>The passage</th><th>Version {changes["from"]}</th><th>Version {version}</th>'
                 f'<th>Papers that state it</th></tr></thead><tbody>{ano_rows}</tbody></table></div>'
                 f'<p class="muted">Open a code\'s "Papers that state it" for each paper\'s sentence, page and link.</p>')
    out = [stats, toc, about,
           f'<h2 id="map">Question and groups</h2><p class="rq">{E(cb["question"])}</p>'
           f'<div class="wrap"><table><thead><tr><th></th><th>Sub-question</th><th>Group</th><th>Codes</th></tr></thead>'
           f'<tbody>{"".join(rows)}</tbody></table></div>']

    glance = "".join(f'<tr><td><a href="#g{g["no"]}">{g["no"]}. {E(g["title"])}</a></td>'
                     f'<td>{E(PLAIN.get(g["name"], g["asks"]))}</td><td>'
                     + "<br>".join(f'<a href="#{c}">{num[c]} {E(labels[c])}</a>{tag(c)}' for c in ids(g))
                     + "</td></tr>" for g in groups)
    glance += '<tr class="sub"><td colspan="3">Worked out from the codes above (level 2)</td></tr>' + "".join(
        f'<tr><td><a href="#{kind}">{title}</a></td><td>{E(asks)}</td><td>'
        + "<br>".join(f'<a href="#{r["id"]}">{E(r["name"])}</a>' for r in cb["levels"]["level2"] if r["kind"] == kind)
        + "</td></tr>" for kind, title, asks in KINDS)
    out.append(f'<h2 id="glance">Groups at a glance</h2><div class="wrap"><table><thead><tr><th>Group</th>'
               f'<th style="width:32%">What it captures</th><th style="width:42%">Codes</th></tr></thead><tbody>{glance}</tbody></table></div>')

    for g in groups:
        out.append(f'<h2 id="g{g["no"]}">{g["no"]}. {E(g["title"])} <span class="sq">{g["sq"]}</span></h2>'
                   f'<p class="asks">{E(g["asks"])}</p>')
        if g["pick_one"]:
            out.append(f'<p class="note">Pick one for each story: {E(g["pick_one"]["asks"])}</p>')
        for c in ids(g):
            code, new = view["codes"][c], added.get(c)
            m = EXAMPLE.search(code["applies_when"])
            use = code["applies_when"][:m.start()] if m else code["applies_when"]
            example = ""
            if m:
                src = f' <span class="muted">({E(m.group(1))})</span>' if m.group(1) else ' <span class="muted">(made up)</span>'
                example = f"<dt>Example</dt><dd>{E(m.group(2).strip())}{src}</dd>"
            moved = ""
            if new and new.get("absorbs"):
                moved = ("<dt>Round-1 anomalies it now covers</dt><dd><ul>"
                         + "".join(f'<li><b>{E(a["anomaly"])}</b> {E(a["comment"])}</li>' for a in new["absorbs"])
                         + "</ul></dd>")
            out.append(f'<article id="{c}" class="code{" new" if new else ""}"><h3><span class="no">{num[c]}</span>'
                       f'{E(code["label"])}{tag(c)}</h3><p>{plain(code.get("definition", ""), labels)}</p><dl>'
                       f'<dt>Use it when</dt><dd>{plain(use, labels)}</dd>{example}'
                       f'<dt>Don\'t use it when</dt><dd>{dont_lines(code, version, changes, new_labels, labels)}</dd>{moved}</dl>'
                       f'{quotes(ev(c), meta, files, evidence.get("linked_only", {}).get(c))}</article>')
        if g["anomaly"]:
            out.append(f'<p class="note"><b>{g["no"]}.A Nothing fits:</b> record an anomaly.</p>')

    l2 = []
    for kind, title, asks in KINDS:
        items = [r for r in cb["levels"]["level2"] if r["kind"] == kind]
        l2.append(f'<h3 id="{kind}">{title}</h3><p class="asks">{asks}</p>')
        for r in items:
            l2.append(f'<article id="{r["id"]}" class="code"><h3>{E(r["name"])}</h3><p>{E(r["in_short"])}</p>'
                      f'<p class="rule">{E(rule_text(r, labels, num))}</p>'
                      f'{quotes(evidence.get("level2", {}).get(r["id"], []), meta, files)}</article>')
    out.append(f'<h2 id="level2">Level 2: worked out from the codes</h2><p class="asks">Not ticked by coders. '
               f'Each follows from the level-1 codes in a story by the rule shown.</p>{"".join(l2)}')

    prow = "".join(f'<tr><td>{refs[p]}</td><td>' + ", ".join(f'<a href="#{c}">{num[c]}</a>' for c in dict.fromkeys(cs))
                   + "</td></tr>" for p, cs in sorted(papers.items()))
    out.append(f'<h2 id="papers">Papers</h2><p class="asks">Each paper, linked, and the codes it states. Open a code '
               f'to see the sentence and page.</p>'
               f'<div class="wrap"><table><thead><tr><th>Paper</th><th>Codes</th></tr></thead><tbody>{prow}</tbody>'
               f'</table></div>')
    if changes:
        rows = "".join(f'<tr><td>{E(a["anomaly"])}</td><td>{E(a["comment"])}</td></tr>'
                       for a in changes["open_anomalies"])
        out.append(f'<h2 id="open">Open anomalies ({len(changes["open_anomalies"])})</h2>'
                   f'<p class="asks">No paper read in full states these. They wait for the inductive phase.</p>'
                   f'<div class="wrap"><table><thead><tr><th>No.</th><th>Why open</th></tr>'
                   f'</thead><tbody>{rows}</tbody></table></div>')
    return n, "".join(out)


def round_body(work: Path, red: Path, view: dict, version: str, follow: str) -> tuple[str, int, int, int, list]:
    """One round from its redacted coding (RED/work, named in RED/key.json), in the round's own order, so
    interviews appear as "Interview 01" and anomalies are numbered as in the anomaly log."""
    num, labels = numbering(view), view["labels"]
    inv = {o: n for n, o in json.loads((red / "key.json").read_text(encoding="utf-8")).items()}
    cases = [dict(c, case_id=inv[c["case_id"]], file=f'Interview {inv[c["case_id"]].split("-")[1]}.txt')
             for c in json.loads((work / "cases.json").read_text(encoding="utf-8"))]
    again = any(c.get("in_round") == "recode" for c in cases)
    work = red / "work"
    uses, rows, anomalies, stories = Counter(), [], [], 0
    group_of = {g["anomaly"]["id"]: g["title"] for g in view["groups"] if g["anomaly"]}
    group_of[view["new"]["id"]] = "Something no group asks about"
    for case in cases:
        k = json.loads((work / "checked" / f"{case['case_id']}.json").read_text(encoding="utf-8"))
        ticked = {d["code"] for d in k["decisions"] if d["ticks"]}
        uses.update(ticked)
        stories += len(k["stories"])
        first = len(anomalies) + 1
        for a in k["anomalies"]:
            anomalies.append((f"A{len(anomalies) + 1:02d}", case, a))
        nos = f"A{first:02d}–A{len(anomalies):02d}" if len(anomalies) > first else \
            (f"A{first:02d}" if len(anomalies) == first else "none")
        codes = ", ".join(sorted((num[c] for c in ticked if c in num), key=lambda s: [int(x) for x in s.split(".")]))
        rows.append(f'<tr><td>{E(name(case))}{" <span class=muted>(again)</span>" if case.get("in_round") == "recode" else ""}</td>'
                    f'<td>{"; ".join(E(s["name"]) for s in k["stories"])}</td><td>{codes}</td><td>{nos}</td></tr>')
    use_rows = "".join(f'<tr><td>{num[c]}</td><td>{E(labels[c])}</td><td>{uses[c]}</td></tr>'
                       for c in sorted((c for c in labels if c in num and not num[c].endswith(".A")),
                                       key=lambda c: [int(x) for x in num[c].split(".")]))
    ano_rows = "".join(f'<tr><td>{no}</td><td>{E(name(case))}</td><td>{E(group_of.get(a["code"], a["code"]))}</td>'
                       f'<td>{E(a["story"])}</td><td>{E(a["label"])}</td><td>{E(a["why"])}</td></tr>'
                       for no, case, a in anomalies)
    body = (f'<h2>Each interview</h2><p class="asks">Stories are the separate episodes a founder tells. Codes are '
            f'numbered as in codebook version {version}.'
            + (' "Again" marks an interview coded in the round before, coded again here.' if again else "")
            + '</p><div class="wrap"><table><thead><tr>'
            f'<th>Interview</th><th>Stories</th><th>Codes ticked</th><th>Anomalies</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<h2>How often each code was used</h2><p class="asks">Number of interviews (of {len(cases)}) where the code '
            f'was ticked at least once.</p><div class="wrap"><table><thead><tr><th>No.</th><th>Code</th>'
            f'<th>Interviews</th></tr></thead><tbody>{use_rows}</tbody></table></div>'
            f'<h2>The {len(anomalies)} anomalies</h2><p class="asks">Passages that matter for the question but that no '
            f'code fits, in the coder\'s words. {follow}</p><div class="wrap"><table><thead><tr>'
            f'<th>No.</th><th>Interview</th><th>Group</th><th>Story</th><th>What it is</th><th>Why no code fits</th>'
            f'</tr></thead><tbody>{ano_rows}</tbody></table></div>')
    return body, len(cases), stories, len(anomalies), anomalies


def name(case: dict) -> str:
    return Path(case["file"]).stem.replace("-", " ").capitalize()


def search_page(changes: dict, log: dict, view2: dict, anomalies: list) -> str:
    num2, labels2 = numbering(view2), view2["labels"]
    where = {}
    for e in changes["codes"]:
        for a in e.get("absorbs", []):
            where[a["anomaly"]] = (f'<span class="tag new">{num2[e["id"]]} {E(labels2[e["id"]])}</span>', a["comment"])
    for a in changes["open_anomalies"]:
        where[a["anomaly"]] = ('<span class="tag open">Still open</span>', a["comment"])
    rows = "".join(f'<tr><td>{no}</td><td>{E(a["label"])}</td><td>{where[no][0]}</td><td>{E(where[no][1])}</td></tr>'
                   for no, case, a in anomalies)
    themes = []
    for t in log["themes"]:
        if not t.get("searches"):
            continue
        s = "".join(f'<li><b>{E(x["date"])}</b>, {E(x["where"])}: <q>{E(x["query"])}</q>. {x["hits"]} found'
                    f'{", kept " + E(", ".join(x["kept"])) if x["kept"] else ", none kept"}.'
                    f'{" " + E(x["note"]) if x["note"] else ""}</li>' for x in t["searches"])
        status = "Adopted as a code" if t["status"] == "adopted" else "Still open"
        themes.append(f'<article class="code"><h3>{E(t["name"])} <span class="tag {"new" if t["status"] == "adopted" else "open"}">'
                      f'{status}</span></h3><p>{E(t["what"])}</p><dl><dt>Searches</dt><dd><ul>{s}</ul></dd></dl></article>')
    moved = sum(1 for v in where.values() if "Still open" not in v[0])
    return (f'<p class="lead"><b>{moved}</b> of {len(anomalies)} anomalies moved into a code backed by papers read in '
            f'full. <b>{len(anomalies) - moved}</b> stay open.</p>'
            f'<h2>Where each anomaly went</h2><div class="wrap"><table><thead><tr><th>No.</th><th>What it is</th>'
            f'<th>Now</th><th>Comment</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<h2>The searches, theme by theme</h2><p class="asks">Each theme was looked for in the papers already read, '
            f'the full-text library and the abstract catalogs. A paper counts only when it was read in full and a '
            f'sentence in it states the idea.</p>{"".join(themes)}')


def reliability_rows(name: str) -> list[dict]:
    return [r for r in csv.DictReader((CB / "reliability" / name).open(encoding="utf-8")) if r["code"] != "anomalies"]


def reliability_text(rel: list[dict], n: int, versions: str, link: str) -> str:
    kap = [float(r["kappa"]) for r in rel if r["kappa"] != ""]
    return (f'{round(100 * sum(float(r["agree"]) for r in rel) / len(rel))}% agreement; mean kappa '
            f'{sum(kap) / len(kap):.2f}; mean AC1 {sum(float(r["ac1"]) for r in rel) / len(rel):.2f} '
            f'({n} interviews, version {versions}, {len(rel)} codes in both) <a href="{link}">(by code)</a>')


def reliability_table(rel: list[dict], a: str, b: str) -> str:
    rows = "".join(f'<tr><td>{r["no"]}</td><td>{E(r["label"])}{" <span class=muted>(reworded)</span>" if r["wording_changed"] == "True" else ""}'
                   f'</td><td>{r["both"]}</td><td>{r["only_a"]}</td><td>{r["only_b"]}</td><td>{r["neither"]}</td>'
                   f'<td>{round(100 * float(r["agree"]))}%</td><td>{r["kappa"]}</td><td>{r["ac1"]}</td></tr>' for r in rel)
    return (f'<div class="wrap"><table><thead><tr><th>No.</th><th>Code</th><th>Both</th><th>{a} only</th>'
            f'<th>{b} only</th><th>Neither</th><th>Agree</th><th>Kappa</th><th>AC1</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def themes_section(themes: dict) -> str:
    rows = "".join(f'<tr><td>{E(t["name"])}</td><td>{E(t["group"])}</td><td>{E(t["what"])}</td>'
                   f'<td>{", ".join(t["anomalies"])}</td><td>{"recurs" if t["verdict"].startswith("Recurs") else "new"}</td></tr>'
                   for t in themes["themes"])
    recur = sum(t["verdict"].startswith("Recurs") for t in themes["themes"])
    return (f'<h2 id="themes">The anomalies grouped into {len(themes["themes"])} themes</h2><p class="asks">Grouped by '
            f'Claude for the researchers to review. {recur} themes recur from earlier rounds and keep their names; the '
            f'rest are new. None was searched in the literature: calibration stops here, and every theme stays open '
            f'for the inductive phase.</p><div class="wrap"><table><thead><tr><th>Theme</th><th>Group</th>'
            f'<th>What it is</th><th>Anomalies</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>')


def n_papers(cb: dict, evidence: dict, meta: dict, files: dict) -> int:
    view = codebook_from(cb)
    codes = [c for g in view["groups"] for c in (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]]
    return len({short(e, meta, files) for c in codes for e in evidence["codes"].get(c, [])})


def progression_page(stages: list[dict]) -> str:
    """One column per codebook version: the codebook, the round coded with it, and where its anomalies went."""
    rows = [("Codebook", None),
            ("Codes coders tick (level 1)", "codes"), ("Added since the version before", "added"),
            ("Worked out from the codes (level 2)", "level2"), ("Papers that state its codes", "papers"),
            ("Coding round", None),
            ("Round", "round"), ("Interviews coded with it", "interviews"), ("Interviews coded so far", "total"),
            ("Stories", "stories"),
            ("Anomalies", None),
            ("Passages no code fit", "anomalies"), ("Moved into a code in the next version", "absorbed"),
            ("Still open", "open"), ("Open so far, for the inductive phase", "open_total"),
            ("Reliability", None), ("The round before's interviews, coded again", "reliability")]
    head = "".join(f'<th><a href="{st["page"]}">Version {st["version"]}</a></th>' for st in stages)
    body = "".join(
        f'<tr class="sub"><td colspan="{len(stages) + 1}">{label}</td></tr>' if key is None else
        f'<tr><td>{label}</td>' + "".join(f'<td>{st.get(key, "")}</td>' for st in stages) + "</tr>"
        for label, key in rows)
    return (f'<div class="wrap"><table class="prog"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody>'
            f'</table></div><p class="muted">Calibration stopped after round 3, so version 3.0 is the last column. Reliability compares the same '
            f'interviews coded in two rounds: agreement is the share of interviews where both codings agree on a code; '
            f'kappa and AC1 correct it for chance (AC1 is not pulled to zero by codes found in nearly every interview). '
            f'Part of the difference comes from the codebook itself changing between the two rounds.</p>')


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    meta = load("paper_metadata.json")
    ev1, ev2, ev3 = load("evidence_v1.0.json"), load("evidence_v2.0.json"), load("evidence_v3.0.json")
    PAPERS.update(ev2.get("papers", {}))
    PAPERS.update(ev3.get("papers", {}))
    files = {e["paper"]: e["text"] for ev in (ev2, ev3) for v in ev["codes"].values() for e in v}
    ev_both = dict(ev1, codes={**ev1["codes"], **ev2["codes"]},
                   linked_only={c: v for c, v in ev1["linked_only"].items() if c not in ev2["codes"]})
    cb1, cb2, changes, log = load("codebook_v1.0.json"), load("codebook_v2.0.json"), load("changes_v2.0.json"), \
        load("anomaly_log.json")
    cb3, changes3 = load("codebook_v3.0.json"), load("changes_v3.0.json")
    ev_all = dict(ev_both, codes={**ev_both["codes"], **ev3["codes"]},
                  linked_only={c: v for c, v in ev_both["linked_only"].items() if c not in ev3["codes"]})
    added3 = {c["id"] for c in cb3["codes"] if c.get("added_in") == "3.0"}
    n_new3 = sum(e["id"] in added3 for e in changes3["codes"])
    moved3 = sum(len(e.get("absorbs", [])) for e in changes3["codes"])
    open3 = [a for a in changes3["open_anomalies"] if a.get("round") == 2]
    view1, view2 = codebook_from(cb1), codebook_from(cb2)
    added2 = {c["id"] for c in cb2["codes"] if c.get("added_in") == "2.0"}
    n_new = sum(e["id"] in added2 for e in changes["codes"])
    conf = DOCS / "outputs" / "review_confidential"
    rounds = {r["round"]: r for r in log["rounds"] if r["coder"] == "model"}
    body3, n_cases, n_stories, n_ano, anomalies = round_body(ROOT / rounds[1]["work"], conf / "round1", view1, "1.0",
                                                             "Page 3 follows each one.")
    work2 = ROOT / rounds[2]["work"]
    body6, n_cases2, n_stories2, n_ano2, anomalies2 = round_body(work2, conf / "round2", view2, "2.0",
                                                                 "They wait for the paper search before version 3.")
    cases2 = json.loads((work2 / "cases.json").read_text(encoding="utf-8"))
    again2 = {c["case_id"] for c in cases2 if c.get("in_round") == "recode"}
    ano_again = sum(len(json.loads((work2 / "checked" / f"{c}.json").read_text(encoding="utf-8"))["anomalies"]) for c in again2)
    rel = reliability_rows("first25_round1_v1.0_vs_round2_v2.0.csv")
    reliability = reliability_text(rel, len(again2), "1.0 then 2.0", "6_round2_coding.html#reliability")
    open_themes = [t for t in log["themes"] if t["status"] == "open"]
    themes2 = {t["id"] for t in open_themes if any(a["round"] == 2 for a in t["anomalies"])}
    carried = {t["id"] for t in open_themes if t["id"] in themes2 and any(a["round"] == 1 for a in t["anomalies"])}
    n_open = len(changes["open_anomalies"])

    n1, body = codebook_page(cb1, "1.0", meta, files, ev1, None)
    (out / "1_codebook_v1.html").write_text(page(
        "Codebook version 1.0", "Built from papers only, before any interview was coded.", body), encoding="utf-8")

    (out / "2_round1_coding.html").write_text(page(
        "Round 1: the first 25 interviews",
        f"{n_cases} Starter Story interviews coded with codebook version 1.0 by Claude (Opus 5.5) on 27 to 29 October "
        f"2026: {n_stories} stories and {n_ano} anomalies. The interview text is not shown, because Starter Story owns it.",
        body3), encoding="utf-8")

    (out / "3_paper_search.html").write_text(page(
        "From anomalies to papers",
        "Each round-1 anomaly was grouped into a theme, and each theme was searched for in the literature. A theme "
        "became a code only if a paper read in full states it, it is one clear idea, it bears on the research "
        "question, and no existing code covers it.", search_page(changes, log, view2, anomalies)), encoding="utf-8")

    n2, body = codebook_page(cb2, "2.0", meta, files, ev_both, changes)
    (out / "4_codebook_v2.html").write_text(page(
        "Codebook version 2.0", "Version 1.0 plus the codes that round 1's anomalies earned. New codes and codes that now cover more "
        "are shaded.", body), encoding="utf-8")

    view3 = codebook_from(cb3)
    work3 = ROOT / rounds[3]["work"]
    body8, n_cases3, n_stories3, n_ano3, _ = round_body(work3, conf / "round3", view3, "3.0",
                                                         "They are grouped into themes below.")
    cases3 = json.loads((work3 / "cases.json").read_text(encoding="utf-8"))
    again3 = {c["case_id"] for c in cases3 if c.get("in_round") == "recode"}
    ano_again3 = sum(len(json.loads((work3 / "checked" / f"{c}.json").read_text(encoding="utf-8"))["anomalies"])
                     for c in again3)
    themes3 = json.loads((work3 / "anomaly_themes.json").read_text(encoding="utf-8"))
    rel3a = reliability_rows("first25_round2_v2.0_vs_round3_v3.0.csv")
    rel3b = reliability_rows("next25_round2_v2.0_vs_round3_v3.0.csv")
    reliability3 = (f"Interviews 01–25: " + reliability_text(rel3a, 25, "2.0 then 3.0", "8_round3_coding.html#reliability")
                    + f"<br>Interviews 26–50: " + reliability_text(rel3b, 25, "2.0 then 3.0", "8_round3_coding.html#reliability"))
    n3, body7 = codebook_page(cb3, "3.0", meta, files, ev_all, changes3)
    (out / "7_codebook_v3.html").write_text(page(
        "Codebook version 3.0", "Version 2.0 plus the codes that round 2's anomalies earned. New codes and codes that "
        "now cover more are shaded.", body7), encoding="utf-8")

    n_moved = n_ano - n_open
    stages = [
        {"version": "1.0", "page": "1_codebook_v1.html", "codes": n1, "added": "first version",
         "level2": len(cb1["levels"]["level2"]), "papers": n_papers(cb1, ev1, meta, files),
         "round": '<a href="2_round1_coding.html">Round 1</a>', "interviews": n_cases, "total": n_cases,
         "stories": n_stories, "anomalies": n_ano,
         "absorbed": f'{n_moved} <a href="3_paper_search.html">(where)</a>', "open": n_open,
         "open_total": f"{n_open} passages", "reliability": "first round"},
        {"version": "2.0", "page": "4_codebook_v2.html", "codes": n2,
         "added": f"{n_new} new codes; {len(changes['codes']) - n_new} existing code now covers more ("
                 + "; ".join(f"{numbering(view2)[e['id']]} {view2['labels'][e['id']]}: {e['extends']['was']} → {e['extends']['now']}"
                             for e in changes["codes"] if e.get("extends")) + ")",
         "level2": len(cb2["levels"]["level2"]), "papers": n_papers(cb2, ev_both, meta, files),
         "round": '<a href="6_round2_coding.html">Round 2</a>',
         "interviews": f"{n_cases2} ({n_cases2 - len(again2)} new, {len(again2)} from round 1 again)",
         "total": len({c["case_id"] for c in cases2}), "stories": n_stories2,
         "anomalies": f"{n_ano2} ({n_ano2 - ano_again} in new interviews, {ano_again} in round 1's)",
         "absorbed": f'{moved3} <a href="7_codebook_v3.html#version">(where)</a>', "open": len(open3),
         "open_total": f"{len(changes3['open_anomalies'])} passages ({len(changes3['open_anomalies']) - len(open3)} from "
                       f"round 1, {len(open3)} from round 2)",
         "reliability": reliability},
        {"version": "3.0", "page": "7_codebook_v3.html", "codes": n3,
         "added": f"{n_new3} new codes; {len(changes3['codes']) - n_new3} existing code now covers more ("
                 + "; ".join(f"{numbering(view3)[e['id']]} {view3['labels'][e['id']]}: {e['extends']['was']} → {e['extends']['now']}"
                             for e in changes3["codes"] if e.get("extends")) + ")",
         "level2": len(cb3["levels"]["level2"]), "papers": n_papers(cb3, ev_all, meta, files),
         "round": '<a href="8_round3_coding.html">Round 3</a> (last calibration round)',
         "interviews": f"{n_cases3} ({n_cases3 - len(again3)} new, {len(again3)} from rounds 1 and 2 again)",
         "total": len({c["case_id"] for c in cases3}), "stories": n_stories3,
         "anomalies": f"{n_ano3} ({n_ano3 - ano_again3} in new interviews, {ano_again3} in earlier rounds')",
         "absorbed": "none: calibration stopped; no version 4.0", "open": n_ano3,
         "open_total": f'all, for the inductive phase; round 3\'s grouped into <a href="8_round3_coding.html#themes">'
                       f'{len(themes3["themes"])} themes</a>',
         "reliability": reliability3}]
    rel_rows = "".join(f'<tr><td>{r["no"]}</td><td>{E(r["label"])}</td><td>{r["both"]}</td><td>{r["only_a"]}</td>'
                       f'<td>{r["only_b"]}</td><td>{r["neither"]}</td><td>{round(100 * float(r["agree"]))}%</td>'
                       f'<td>{r["kappa"]}</td><td>{r["ac1"]}</td></tr>' for r in rel)
    body6 += (f'<h2 id="reliability">Reliability: round 1\'s interviews coded again</h2><p class="asks">The {len(again2)} '
              f'interviews of round 1 were coded again, blind, with version 2.0. For each code in both versions: '
              f'interviews where both codings tick it, only round 1, only round 2, neither; agreement; kappa; AC1. '
              f'Some differences are passages that moved to a code new in version 2.0.</p><div class="wrap"><table>'
              f'<thead><tr><th>No.</th><th>Code</th><th>Both</th><th>Round 1 only</th><th>Round 2 only</th>'
              f'<th>Neither</th><th>Agree</th><th>Kappa</th><th>AC1</th></tr></thead><tbody>{rel_rows}</tbody></table></div>')
    body8 += themes_section(themes3)
    body8 += (f'<h2 id="reliability">Reliability: rounds 1 and 2\'s interviews coded again</h2><p class="asks">Each '
              f'earlier interview was coded again, blind, with version 3.0 and compared with its round-2 coding '
              f'(version 2.0). Interviews 01–25 have now been coded three times; interviews 26–50 twice. Codes marked '
              f'"reworded" changed wording between versions, so part of their difference comes from the codebook: 8.5 '
              f'now also covers effort credited alongside luck, so round 3 ticks it far more often.</p>'
              f'<h3>Interviews 01–25 (round 1\'s)</h3>' + reliability_table(rel3a, "Round 2", "Round 3")
              + f'<h3>Interviews 26–50 (round 2\'s new ones)</h3>' + reliability_table(rel3b, "Round 2", "Round 3"))
    (out / "8_round3_coding.html").write_text(page(
        "Round 3: 25 new interviews and rounds 1 and 2's again",
        f"{n_cases3} interviews coded with codebook version 3.0 by Claude (Opus 5.5) on 31 October 2026: "
        f"{n_cases3 - len(again3)} new and the {len(again3)} of rounds 1 and 2 coded again, blind. {n_stories3} stories, "
        f"{n_ano3} anomalies. This is the last calibration round: its anomalies are grouped into themes and kept open "
        f"for the inductive phase. Interview text is not shown, because Starter Story owns it.", body8), encoding="utf-8")

    (out / "6_round2_coding.html").write_text(page(
        "Round 2: 25 new interviews and round 1's again",
        f"{n_cases2} interviews coded with codebook version 2.0 by Claude (Opus 5.5) on 31 October 2026: "
        f"{n_cases2 - len(again2)} new and the {len(again2)} of round 1 coded again, blind. {n_stories2} stories, "
        f"{n_ano2} anomalies. Interview text is not shown, because Starter Story owns it.", body6), encoding="utf-8")

    (out / "5_progression.html").write_text(page(
        "How the codebook grew", "Each codebook version, the round coded with it, and what became of the passages "
        "no code fit.", progression_page(stages)), encoding="utf-8")

    steps = [("1_codebook_v1.html", "Codebook version 1.0", f"{n1} codes, built from papers only."),
             ("2_round1_coding.html", "Round 1: the first 25 interviews",
              f"Coded with version 1.0: {n_stories} stories, {n_ano} anomalies."),
             ("3_paper_search.html", "From anomalies to papers",
              "Each anomaly searched for in the literature, and where it went."),
             ("4_codebook_v2.html", "Codebook version 2.0",
              f"{n2} codes: version 1.0 plus {n_new} new codes; {len(changes['codes']) - n_new} existing code now covers more."),
             ("5_progression.html", "How the codebook grew",
              "One table: each version, its round, where the anomalies went, and reliability."),
             ("6_round2_coding.html", "Round 2: 25 new interviews and round 1's again",
              f"Coded with version 2.0: {n_stories2} stories, {n_ano2} anomalies, and reliability on round 1's interviews."),
             ("7_codebook_v3.html", "Codebook version 3.0",
              f"{n3} codes: version 2.0 plus {n_new3} new codes; {len(changes3['codes']) - n_new3} existing code now covers more."),
             ("8_round3_coding.html", "Round 3: 25 new interviews and rounds 1 and 2's again",
              f"Coded with version 3.0: {n_stories3} stories, {n_ano3} anomalies in {len(themes3['themes'])} themes, and "
              f"reliability for each earlier round. The last calibration round.")]
    items = "".join(f'<li><a href="{f}"><b>{E(t)}</b></a><br><span class="muted">{E(d)}</span></li>' for f, t, d in steps)
    (out / "index.html").write_text(page(
        "How the codebook was built",
        "Read the pages in order. Each step uses only what the step before it produced.",
        f'<ol class="steps">{items}</ol>'), encoding="utf-8")
    print(f"wrote {out}: v1 {n1} codes, round 1 {n_cases} interviews / {n_ano} anomalies, v2 {n2} codes")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#fff; --fg:#1d2329; --muted:#5d6670; --line:#d5dbe1; --head:#1f3a5f; --tint:#eef2f6; --new:#1e6b3a; --newbg:#e8f4ec; --open:#8a5a00; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42; --head:#2c4f7a; --tint:#1c232b; --new:#7fd19b; --newbg:#18281e; --open:#e0b060; }} }}
:root[data-theme="dark"] {{ --bg:#14181c; --fg:#e4e8ec; --muted:#9aa4ae; --line:#323a42; --head:#2c4f7a; --tint:#1c232b; --new:#7fd19b; --newbg:#18281e; --open:#e0b060; }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.55 system-ui, -apple-system, Segoe UI, sans-serif; margin:0; padding:24px 16px; }}
main {{ max-width:900px; margin:0 auto; }}
nav {{ font-size:13px; margin-bottom:12px; }} a {{ color:var(--head); }}
h1 {{ font-size:26px; margin:0 0 6px; }} h2 {{ font-size:20px; margin:36px 0 4px; border-bottom:2px solid var(--line); padding-bottom:4px; }}
h3 {{ font-size:16px; margin:0 0 6px; }} .no {{ color:var(--muted); font-weight:400; margin-right:6px; }}
p.intro {{ color:var(--muted); margin:0 0 20px; }} p.asks {{ color:var(--muted); margin:0 0 12px; }}
p.lead {{ font-size:17px; }} .note {{ background:var(--tint); padding:8px 12px; border-radius:6px; }}
article.code {{ border:1px solid var(--line); border-radius:8px; padding:12px 14px; margin:10px 0; }}
article.new {{ border-color:var(--new); background:var(--newbg); }}
dl {{ margin:0; }} dt {{ font-weight:600; font-size:13px; color:var(--muted); margin-top:8px; }} dd {{ margin:2px 0 0; }}
ol, ul {{ margin:2px 0; padding-left:20px; }} li {{ margin-bottom:4px; }} q {{ font-style:italic; }}
.tag {{ font-size:12px; font-weight:600; border-radius:10px; padding:1px 8px; margin-left:8px; white-space:nowrap; }}
.tag.new {{ color:var(--new); border:1px solid var(--new); }} .tag.rev {{ color:var(--head); border:1px solid var(--head); }}
.tag.open {{ color:var(--open); border:1px solid var(--open); }} .muted {{ color:var(--muted); font-size:13px; }}
.wrap {{ overflow-x:auto; }} table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th {{ background:var(--head); color:#fff; text-align:left; padding:6px 8px; }}
td {{ border:1px solid var(--line); padding:6px 8px; vertical-align:top; }}
ol.steps li {{ margin-bottom:14px; font-size:16px; }}
.stats {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 14px; }}
.stats span {{ background:var(--tint); border-radius:6px; padding:4px 10px; }}
nav.toc {{ display:flex; flex-wrap:wrap; gap:4px 14px; font-size:14px; padding:10px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }}
p.rq {{ font-size:18px; font-weight:600; }} .sq {{ font-size:13px; color:var(--muted); font-weight:400; margin-left:6px; }}
article p {{ margin:0 0 4px; }} p.rule {{ font-family:ui-monospace, Menlo, monospace; font-size:13px; color:var(--muted); }}
table.prog td:not(:first-child), table.prog th:not(:first-child) {{ text-align:center; }} th a {{ color:#fff; }}
tr.sub td {{ background:var(--tint); font-weight:600; }} details {{ margin-top:8px; }}
.src {{ font-size:11px; color:var(--muted); background:var(--tint); border-radius:8px; padding:0 6px; white-space:nowrap; }}
.version {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px; margin:16px 0; }}
.version > div {{ background:var(--tint); border-radius:8px; padding:10px 14px; }} .version h3 {{ margin:0 0 4px; }}
.version ul {{ font-size:14px; }} summary {{ cursor:pointer; color:var(--head); font-size:14px; font-weight:600; }}
.lean {{ color:var(--open); font-size:12px; }} h2 {{ scroll-margin-top:12px; }} article {{ scroll-margin-top:12px; }}
</style></head><body><main>
<nav><a href="index.html">How the codebook was built</a></nav>
<h1>{title}</h1><p class="intro">{intro}</p>
{body}
</main></body></html>
"""

if __name__ == "__main__":
    main()
