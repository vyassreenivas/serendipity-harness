"""Build the codebook review workbook, and turn an edited workbook back into review.csv.

Usage:
  python workbook.py build codebook_review.xlsx      write (or rebuild) the workbook
  python workbook.py review codebook_review.xlsx     write harness/codebook/review.csv from it

Two sheets hold the codes, and each column has one home:
  Codebook   the core codes and the anomaly codes. Edit the wording and the
             reason here.
  All codes  every drafted code. Edit Status here: core, reference or reject.
             Wording is edited here only for reference codes.
Rebuilding an existing workbook keeps every edit (the old file is kept as .bak)
and moves codes onto or off the Codebook sheet to match their Status.
`review` works out accept or revise by comparing the wording with the draft,
checks the entries, and writes the review sheet `freeze` reads. It never
overwrites an existing review.csv.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from export import ADDED, DRAFT, GROUPS, H, MISFIT, REVIEW, best_sentence, cite, repair

FONT, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
GREYED = Font(name="Arial", size=10, color="8C8C8C")
HEAD = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F3A5F")
EDIT_FILL = PatternFill("solid", fgColor="FFF2B3")
LINK = Font(name="Arial", size=10, color="1F5FA8", underline="single")
WRAP = Alignment(wrap_text=True, vertical="top")
SQTEXT = {"SQ1": "What counts as serendipity?", "SQ2": "Where does it happen, and what sets it off?",
          "SQ3": "What do founders bring and do?", "SQ4": "What does it change in the venture?",
          "SQ5": "When is it more or less likely?", "SQ6": "How do founders tell it?", "all": "All sub-questions"}
EXAMPLE = re.compile(r"\s*For example:\s*(.+)$")
WORDING = ["Label", "Description", "Code it when", "Example (made up)", "Not when"]
STATUSES = ("core", "reference", "reject")
PICKS_FILE = H / "codebook" / "evidence_picks.json"
_picks = json.loads(PICKS_FILE.read_text(encoding="utf-8")) if PICKS_FILE.exists() else {}
PICKS = _picks.get("picks", {})          # the sentence shown first for a code
ALSO = _picks.get("also", {})            # further sentences chosen by reading, one per paper
NONE = _picks.get("none", {})            # works where reading found no sentence that states the code
NO_SENTENCE = "(no sentence in the cited passages states this code; checked by reading)"

# Word limits that keep the coder view short; longer wording is shaded on the Codebook sheet.
LIMITS = {"Label": 5, "Code it when": 20, "Example (made up)": 20, "Not when": 15}
LONG_FILL = PatternFill("solid", fgColor="F8CBAD")
GROUP_FILL = PatternFill("solid", fgColor="DCE6F1")
# Codebook columns shown while reviewing; the rest are hidden, one click away (+ above the columns).
REVIEW_HIDDEN = ["Sub-question", "Description", "Papers", "Page", "Sentence chosen by",
                 "Draft wording (before revision)"]

NEW_REASON = "New: from the six papers read on 21 Oct 2026 (harness/codebook/added_papers.json)."


def load_draft() -> dict[str, dict]:
    """The 360-code draft plus the papers read after it (added_papers.json): their matches add
    papers and passages to existing codes, and their new codes join as reference codes."""
    draft = {c["id"]: c for c in json.loads(DRAFT.read_text(encoding="utf-8"))["codes"]}
    for m in ADDED["maps"]:
        d = draft[m["code"]]
        paper = m["candidate_id"].split(":")[0]
        d["papers"] = d["papers"] + ([paper] if paper not in d["papers"] else [])
        d["passage_ids"] = d["passage_ids"] + [p for p in m["passage_ids"] if p not in d["passage_ids"]]
    for n in ADDED["new_codes"]:
        draft[n["id"]] = {"id": n["id"], "group": n["group"], "label": n["label"], "definition": n["definition"],
                          "applies_when": n["applies_when"], "does_not_apply_when": n["does_not_apply_when"],
                          "papers": [n["candidate_id"].split(":")[0]], "passage_ids": n["passage_ids"]}
    return draft


def new_state(d: dict) -> dict:
    return {"Status": "reference", "Reason": NEW_REASON, "Label": d["label"], "Description": d["definition"],
            "Code it when": d["applies_when"], "Example (made up)": "", "Not when": d["does_not_apply_when"]}


# header, width, editable
BOOK_COLS = [("Group", 12, False), ("Sub-question", 22, False), ("Code ID", 14, False),
             ("Label", 26, True), ("Description", 48, True), ("Code it when", 44, True),
             ("Example (made up)", 34, True), ("Not when", 40, True), ("Reason", 34, True),
             ("Papers", 8, False), ("Evidence sentence", 60, False), ("From", 22, False), ("Page", 6, False),
             ("Sentence chosen by", 14, False), ("Draft wording (before revision)", 46, False)]
ALL_COLS = [("Group #", 7, False), ("Group", 12, False), ("Code ID", 14, False), ("Status", 11, True),
            ("Reason", 34, True), ("Label", 26, True), ("Description", 48, True), ("Code it when", 44, True),
            ("Example (made up)", 34, True), ("Not when", 40, True), ("Papers", 8, False),
            ("Best evidence sentence", 60, False), ("From", 22, False), ("Page", 6, False),
            ("All supporting papers", 46, False)]


def header(ws, cols, freeze_col):
    for j, (name, width, _) in enumerate(cols, 1):
        c = ws.cell(row=1, column=j, value=name)
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, WRAP
        ws.column_dimensions[get_column_letter(j)].width = width
    ws.freeze_panes = ws.cell(row=2, column=freeze_col)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}1"


def text(v) -> str:
    return v.strip() if isinstance(v, str) else ("" if v is None else str(v))


def evidence_for(code: dict) -> list[dict]:
    """One entry per supporting work, most supporting passages first, with its best sentence.
    Where a sentence was chosen by reading (evidence_picks.json), that work comes first and
    carries the chosen sentence."""
    by_paper: dict[str, list[str]] = {}
    for pid in code["passage_ids"]:
        by_paper.setdefault(pid.split(":")[0], []).append(pid)
    works: dict[str, dict] = {}
    for p in code["papers"]:
        c = cite(p)
        w = works.setdefault(c["short"] + c["url"], dict(c, pids=[]))
        w["pids"] += by_paper.get(p, [])
    out = []
    for w in sorted(works.values(), key=lambda w: -len(w["pids"])):
        out.append(dict({k: v for k, v in w.items() if k != "pids"},
                        quote=best_sentence(code, w["pids"]), passages=len(w["pids"]), chosen=False, close=False))
    chosen = ALSO.get(code["id"], []) + ([PICKS[code["id"]]] if code["id"] in PICKS else [])
    for k, pick in enumerate(chosen):  # the primary pick is applied last, so its work ends up first
        c = cite(pick["passage_id"].split(":")[0])
        for i, e in enumerate(out):
            if e["short"] + e["url"] == c["short"] + c["url"]:
                e["quote"] = {"text": repair(pick["text"]), "pdf_page": pick["pdf_page"], "passage_id": pick["passage_id"]}
                e["chosen"] = True
                e["close"] = pick.get("match") == "close"
                if k == len(chosen) - 1 and code["id"] in PICKS:
                    out.insert(0, out.pop(i))
                break
    for e in out:  # reading found nothing that states the code: say so rather than quote off-topic text
        if not e["chosen"] and e["short"] + e["url"] in NONE.get(code["id"], []):
            e["quote"], e["chosen"], e["none"] = None, True, True
    out.sort(key=lambda e: bool(e.get("none")))  # those rows go last
    return out


def chooser(e: dict) -> str:
    """Who chose the sentence; a close match only leans on the code and is flagged."""
    return ("reading" if e["chosen"] else "fixed code") + ("; close match" if e.get("close") else "")


def state_from_csv() -> dict[str, dict]:
    """Starting state: the suggested (or saved) review sheet."""
    state = {}
    for r in csv.DictReader(open(REVIEW, encoding="utf-8")):
        applies, example = r["applies_when"], ""
        m = EXAMPLE.search(applies)
        if m:
            applies, example = applies[:m.start()].strip(), m.group(1).strip()
        status = "reject" if r["decision"] == "reject" else ("core" if r["core"] == "yes" else "reference")
        state[r["id"]] = {"Status": status, "Reason": r["reason"], "Label": r["label"], "Description": r["definition"],
                          "Code it when": applies, "Example (made up)": example, "Not when": r["does_not_apply_when"]}
    return state


def state_from_workbook(path: str) -> dict[str, dict]:
    """Current state of an edited workbook: Status from All codes; wording and reason from the
    Codebook sheet for codes on it, from All codes for the rest."""
    wb = load_workbook(path)
    rows = {}
    for name in ("All codes", "Codebook"):
        ws = wb[name]
        cols = {c.value: i for i, c in enumerate(ws[1])}
        for cells in ws.iter_rows(min_row=2, values_only=True):
            cid = text(cells[cols["Code ID"]])
            if not cid or cid.startswith(("ANO-", "MIS-")):  # anomaly codes (MIS- before 23 Oct) are fixed, not edited here
                continue
            rec = rows.setdefault(cid, {})
            if name == "All codes":
                rec["Status"] = text(cells[cols["Status"]]).lower()
                for k in WORDING + ["Reason"]:
                    rec.setdefault(k, text(cells[cols[k]]))
            else:
                rec["_on_codebook"] = True
                for k in WORDING + ["Reason"]:
                    rec[k] = text(cells[cols[k]])  # the Codebook sheet wins
    return rows


def write_row(ws, r, cols, vals, link_col=None, url=""):
    for j, v in enumerate(vals, 1):
        c = ws.cell(row=r, column=j, value=v)
        c.alignment, c.font = WRAP, FONT
        if cols[j - 1][2]:
            c.fill = EDIT_FILL
    if url and link_col:
        ws.cell(row=r, column=link_col).hyperlink = url
        ws.cell(row=r, column=link_col).font = LINK


def words_in(t: str) -> int:
    return len(t.split())


def coder_view(wb, code_rows: list[tuple[str, int]], col: dict[str, str]) -> None:
    """First tab: the codebook as coders use it, one short line per code under its group.
    Every cell is a formula on the Codebook sheet, so edits there show here at once."""
    ws = wb.create_sheet("Coder view", 0)
    cols = [("Code", 26, "Label"), ("Code it when", 52, "Code it when"), ("Example (made up)", 42, "Example (made up)"),
            ("Not when", 40, "Not when"), ("Papers", 8, "Papers"), ("Code ID", 13, "Code ID")]
    header(ws, [(h, w, False) for h, w, _ in cols], 1)
    ws.auto_filter.ref = None
    r = 2
    for gi, (name, sq, asks) in enumerate(GROUPS, 1):
        rows = [rb for g, rb in code_rows if g == name]
        if not rows:
            continue
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(cols))
        c = ws.cell(row=r, column=1, value=f"{gi}. {name.capitalize()}: {asks}")
        c.font, c.fill, c.alignment = BOLD, GROUP_FILL, Alignment(vertical="center")
        ws.row_dimensions[r].height = 20
        r += 1
        for rb in rows:
            for j, (_, _, src) in enumerate(cols, 1):
                ref = f"Codebook!{col[src]}{rb}"
                c = ws.cell(row=r, column=j, value=f'=IF({ref}="","",{ref})')
                c.font = BOLD if j == 1 else (Font(name="Arial", size=9, color="7F7F7F") if j >= 5 else FONT)
                c.alignment = WRAP
            r += 1
    ws.freeze_panes = "A2"
    ws.print_title_rows = "1:1"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def build(path: str) -> None:
    if Path(path).exists():
        state = state_from_workbook(path)
        shutil.copy(path, path + ".bak")
        source = f"{Path(path).name} (edits kept; previous version saved as .bak)"
    else:
        state, source = state_from_csv(), REVIEW.name
    draft = load_draft()
    for cid, d in draft.items():
        state.setdefault(cid, new_state(d))
    wb = Workbook()

    # ---- Read me
    ws = wb.active
    ws.title = "Read me"
    ws.column_dimensions["A"].width = 110
    lines = [
        ("Serendipity codebook: review workbook (pilot, version 1.0)", Font(name="Arial", size=14, bold=True, color="1F3A5F")),
        (f"Built from the 360-code draft (run 20261012-124904) and {source}.", FONT),
        ("", FONT),
        ("Sheets", BOLD),
        ("Coder view (first tab): the codebook as coders use it. One short line per core code under its group: the code, when to code it, a made-up example, the nearest look-alike, and how many papers back it. It reads from the Codebook sheet, so edit there, not here. Prints landscape.", FONT),
        ("Codebook: the codes coders apply (core) and the 10 anomaly codes. This is the codebook to discuss and agree. Under each code, one row per supporting paper gives its evidence sentence, page and link; they open collapsed; click + beside a code, or the outline button 2 (top left), to show them. Columns you rarely need (sub-question, description, page, who chose the sentence, draft wording) are hidden; click + above the columns to show them.", FONT),
        ("Groups: the 11 code groups in sub-question order, with counts that update as Status changes.", FONT),
        ("All codes: every drafted code (360) and the anomaly codes. Core codes show greyed wording; their wording lives on the Codebook sheet.", FONT),
        ("Evidence: one row per code and supporting paper, with the sentence that best states the code, its PDF page and a link.", FONT),
        ("Sources: every cited work, ranked by how many core codes it backs, with its link.", FONT),
        ("", FONT),
        ("What to edit (yellow cells only)", BOLD),
        ("Codebook sheet: Label, Description, Code it when, Example, Not when, and Reason. Change the wording here for core codes.", FONT),
        ("All codes sheet: Status (core, reference or reject) and Reason. Wording here only for reference codes.", FONT),
        ("Status. core: coders apply it to every episode (aim for about 4 per group; coders handle 30 to 40 codes at once). "
         "reference: kept in the record and used when reviewing anomalies, not applied. reject: removed, for example as a duplicate.", FONT),
        ("Word limits keep the coder view short: Label 5 words, Code it when 20, Example 20, Not when 15. Wording over its limit is shaded orange on the Codebook sheet.", FONT),
        ("Reason: needed when you reject a code or change its wording. For reject, name the code it duplicates, e.g. 'Duplicate of rival-01'.", FONT),
        ("Example: to promote type-23 to core, set its Status to core on All codes with a reason, then rebuild; it moves onto the Codebook sheet.", FONT),
        ("", FONT),
        ("Commands (run in harness_v2/docs/codebook)", BOLD),
        ("Rebuild after changing Status: python workbook.py build codebook_review.xlsx (keeps every edit; the old file is kept as .bak).", FONT),
        ("When agreed: python workbook.py review codebook_review.xlsx. It checks the entries and writes harness/codebook/review.csv for freeze.", FONT),
        ("", FONT),
        ("Where the content comes from", BOLD),
        ("Status suggestions and the plain wording of core codes: Claude Opus 5.5, criteria in harness/codebook/review_suggested_README.md. Suggestions until you confirm them.", FONT),
        ("Evidence sentences are copied from the extracted PDF text. Words the PDF split apart are rejoined by a fixed rule that uses the papers themselves as the dictionary (export.py, repair); nothing else is changed. For the core codes, Claude Opus 5.5 chose the sentence that best states the code from the eight best candidates (harness/codebook/evidence_picks.json). For other rows, fixed code chose it (export.py, best_sentence). The Evidence sheet says which.", FONT),
        ("Six papers were read after the draft (21 Oct 2026): Grimes (2018), Kirtley and O'Mahony (2023), Shah and Tripsas (2007), Plowman et al. (2007), Oo et al. (2025) and Terveen (2025). Claude Opus 5.5 read them in a Claude Code session with the harness's own extraction prompt and passage checks (run 20261021-003947). Their evidence is added under the codes they match; 'close match' marks a paper that only leans on a code. Nine new codes join as reference codes with the reason 'New'. Details: harness/codebook/added_papers.json and inapp_mapping_20261021.csv.", FONT),
        ("Examples are made up for illustration; they are not quotes from the interviews.", FONT),
    ]
    for i, (t, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=t)
        c.font, c.alignment = font, Alignment(wrap_text=True, vertical="top")

    wbook = wb.create_sheet("Codebook")
    header(wbook, BOOK_COLS, 4)
    wg = wb.create_sheet("Groups")
    wall = wb.create_sheet("All codes")
    header(wall, ALL_COLS, 4)
    evidence_rows, works = [], {}
    rb = ra = 2
    code_rows: list[tuple[str, int]] = []
    for gi, (name, sq, _asks) in enumerate(GROUPS, 1):
        sqt = SQTEXT[sq] if sq == "all" else f"{sq} {SQTEXT[sq]}"
        if name == "anomaly":
            for m in MISFIT["codes"]:
                write_row(wbook, rb, [(h, w, False) for h, w, _ in BOOK_COLS],
                          [name, sqt, m["id"], m["label"], "", m["applies_when"], "", m["does_not_apply_when"],
                           "Agreed in Stage 1 (fixed)", "", "", "", "", "", ""])
                for j in (1, 3, 4):
                    wbook.cell(row=rb, column=j).font = BOLD
                code_rows.append((name, rb))
                write_row(wall, ra, [(h, w, False) for h, w, _ in ALL_COLS],
                          [gi, name, m["id"], "core", "Agreed in Stage 1 (fixed)", m["label"], "", m["applies_when"], "",
                           m["does_not_apply_when"], "", "", "", "", ""])
                rb += 1; ra += 1
            continue
        ids = sorted((i for i in draft if draft[i]["group"] == name),
                     key=lambda i: (STATUSES.index(state[i]["Status"]) if state[i]["Status"] in STATUSES else 9,
                                    int(i.split("-")[1])))
        for cid in ids:
            d, s = draft[cid], state[cid]
            ev = evidence_for(d)
            top = next((e for e in ev if e["quote"]), None)
            ev_vals = [len(ev), top["quote"]["text"] if top else "", top["short"] if top else "",
                       top["quote"]["pdf_page"] if top else "", "; ".join(e["short"] for e in ev)]
            url = top["url"] if top else ""
            words = [s[k] for k in WORDING]
            if s["Status"] == "core":
                changed = s["Description"] != d["definition"] or s["Label"] != d["label"]
                first = [len(ev), top["quote"]["text"] if top else "", top["short"] if top else "",
                         top["quote"]["pdf_page"] if top else "",
                         chooser(top) if top else ""]
                write_row(wbook, rb, BOOK_COLS, [name, sqt, cid] + words + [s["Reason"]] + first +
                          [f"{d['label']}: {d['definition']}" if changed else ""], 12, url)
                for j in (1, 3, 4):
                    wbook.cell(row=rb, column=j).font = BOLD
                code_rows.append((name, rb))
                rb += 1
                for e in ev:  # every other supporting paper, one row each, collapsible under the code
                    if e is top:
                        continue
                    vals = [""] * 10 + [e["quote"]["text"] if e["quote"] else (NO_SENTENCE if e.get("none") else "(no single sentence; see the passages)"),
                                        e["short"], e["quote"]["pdf_page"] if e["quote"] else "",
                                        chooser(e), ""]
                    write_row(wbook, rb, [(h, w, False) for h, w, _ in BOOK_COLS], vals, 12, e["url"])
                    for j in (11, 13, 14):
                        wbook.cell(row=rb, column=j).font = Font(name="Arial", size=9, color="404040")
                    wbook.row_dimensions[rb].outlineLevel = 1
                    wbook.row_dimensions[rb].hidden = True  # opens collapsed: one line per code
                    rb += 1
            write_row(wall, ra, ALL_COLS, [gi, name, cid, s["Status"], s["Reason"]] + words + ev_vals, 13, url)
            if s["Status"] == "core":  # wording lives on the Codebook sheet
                for j in range(6, 11):
                    cell = wall.cell(row=ra, column=j)
                    cell.fill, cell.font = PatternFill(fill_type=None), GREYED
            ra += 1
            for e in ev:
                evidence_rows.append([cid, s["Label"], name, s["Status"], e["short"], e["title"], e["venue"], e["url"],
                                      e["quote"]["pdf_page"] if e["quote"] else "",
                                      e["quote"]["text"] if e["quote"] else (NO_SENTENCE if e.get("none") else "(no single sentence; see the passages)"),
                                      e["quote"]["passage_id"] if e["quote"] else "", e["passages"],
                                      chooser(e).replace("reading", "reading (Claude)", 1)])
                w = works.setdefault(e["short"] + e["url"], {**{k: e[k] for k in ("short", "title", "venue", "url")}, "codes": set()})
                w["codes"].add(cid)
    wbook.sheet_properties.outlinePr.summaryBelow = False  # the +/- button sits on the code's own row
    wbook.sheet_format.outlineLevelRow = 1
    col = {h: get_column_letter(j) for j, (h, _, _) in enumerate(BOOK_COLS, 1)}
    for h in REVIEW_HIDDEN:
        wbook.column_dimensions[col[h]].outlineLevel = 1
        wbook.column_dimensions[col[h]].hidden = True
    wbook.sheet_format.outlineLevelCol = 1
    for h, limit in LIMITS.items():  # shade wording over its word limit
        c = col[h]
        rule = FormulaRule(formula=[f'LEN(TRIM({c}2))-LEN(SUBSTITUTE(TRIM({c}2)," ",""))+1>{limit}'],
                           fill=LONG_FILL)
        wbook.conditional_formatting.add(f"{c}2:{c}{rb - 1}", rule)
    coder_view(wb, code_rows, col)
    last = ra - 1
    dv = DataValidation(type="list", formula1='"core,reference,reject"', allow_blank=False)
    wall.add_data_validation(dv)
    dv.add(f"D2:D{last}")

    # ---- Groups: counts are formulas on the All codes sheet
    gcols = [("#", 5, False), ("Group", 13, False), ("Sub-question", 34, False),
             ("Question asked of each episode", 44, False), ("Core", 8, False), ("Reference", 10, False),
             ("Rejected", 9, False), ("All codes", 9, False)]
    header(wg, gcols, 1)
    rng = lambda col: f"'All codes'!${col}$2:${col}${last}"
    for i, (name, sq, asks) in enumerate(GROUPS, 2):
        vals = [i - 1, name, SQTEXT[sq] if sq == "all" else f"{sq} {SQTEXT[sq]}", asks,
                f'=COUNTIFS({rng("B")},B{i},{rng("D")},"core")',
                f'=COUNTIFS({rng("B")},B{i},{rng("D")},"reference")',
                f'=COUNTIFS({rng("B")},B{i},{rng("D")},"reject")',
                f'=COUNTIFS({rng("B")},B{i})']
        for j, v in enumerate(vals, 1):
            c = wg.cell(row=i, column=j, value=v)
            c.font, c.alignment = (BOLD if j == 2 else FONT), WRAP
    t = len(GROUPS) + 2
    wg.cell(row=t, column=4, value="Total").font = BOLD
    for j, col in ((5, "E"), (6, "F"), (7, "G"), (8, "H")):
        wg.cell(row=t, column=j, value=f"=SUM({col}2:{col}{t - 1})").font = BOLD

    # ---- Evidence
    we = wb.create_sheet("Evidence")
    ecols = [("Code ID", 14, False), ("Label", 26, False), ("Group", 12, False), ("Status", 10, False),
             ("Paper", 24, False), ("Title", 44, False), ("Journal or book", 28, False), ("Link", 30, False),
             ("Page", 6, False), ("Sentence that best states the code", 70, False), ("Passage", 26, False),
             ("Supporting passages", 10, False), ("Sentence chosen by", 16, False)]
    header(we, ecols, 1)
    for i, vals in enumerate(evidence_rows, 2):
        write_row(we, i, ecols, vals, 8, vals[7])

    # ---- Sources
    wsrc = wb.create_sheet("Sources")
    scols = [("Paper", 26, False), ("Title", 60, False), ("Journal or book", 34, False), ("Link", 34, False),
             ("Core codes it backs", 10, False), ("Which core codes", 44, False), ("All codes citing it", 10, False)]
    header(wsrc, scols, 1)
    core_ids = {i for i, st in state.items() if st["Status"] == "core"}
    ranked = sorted(works.values(), key=lambda w: (-len(w["codes"] & core_ids), w["short"].lower()))
    for i, w in enumerate(ranked, 2):
        backs = sorted(w["codes"] & core_ids)
        write_row(wsrc, i, scols, [w["short"], w["title"], w["venue"], w["url"], len(backs), ", ".join(backs),
                                   len(w["codes"])], 4, w["url"])

    wb.calculation.fullCalcOnLoad = True
    wb.save(path)
    core = sum(1 for s in state.values() if s["Status"] == "core")
    long = {h: sum(words_in(s[h]) > n for s in state.values() if s["Status"] == "core") for h, n in LIMITS.items()}
    print("core codes over the word limit: " + ", ".join(f"{h} {k}" for h, k in long.items()))
    print(f"wrote {path}: {core} core + {len(MISFIT['codes'])} anomaly on Codebook; {last - 1} on All codes; "
          f"{len(evidence_rows)} evidence rows; {len(works)} works")


def review(path: str) -> None:
    out = H / "codebook" / "review.csv"
    if out.exists():
        raise SystemExit(f"{out} already exists; move it aside first so nothing is overwritten silently.")
    draft = load_draft()
    state = state_from_workbook(path)
    problems, rows = [], []
    for cid, d in draft.items():
        s = state.get(cid)
        if s is None:
            problems.append(f"{cid}: missing from the workbook")
            continue
        status = s["Status"]
        if status not in STATUSES:
            problems.append(f"{cid}: Status must be core, reference or reject")
            continue
        if status == "core" and not s.get("_on_codebook"):
            problems.append(f"{cid}: marked core but not on the Codebook sheet; rebuild the workbook first")
        if status != "core" and s.get("_on_codebook"):
            problems.append(f"{cid}: on the Codebook sheet but not core; rebuild the workbook first")
        applies = s["Code it when"] + (f" For example: {s['Example (made up)']}" if s["Example (made up)"] else "")
        wording = {"label": s["Label"], "definition": s["Description"], "applies_when": applies,
                   "does_not_apply_when": s["Not when"]}
        changed = any(wording[k].split() != d[k].split() for k in wording)
        decision = "reject" if status == "reject" else ("revise" if changed else "accept")
        if decision != "accept" and not s["Reason"]:
            problems.append(f"{cid}: {'rejecting' if decision == 'reject' else 'changing the wording'} needs a reason")
        rows.append({"id": cid, "group": d["group"], **wording,
                     "papers": "; ".join(d["papers"]), "paper_ids": "; ".join(d["papers"]),
                     "decision": decision, "core": "" if decision == "reject" else ("yes" if status == "core" else "no"),
                     "reason": s["Reason"]})
    if problems:
        raise SystemExit("Not written. Fix these in the workbook:\n  " + "\n  ".join(problems[:40]))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}: {len(rows)} codes, {sum(r['core'] == 'yes' for r in rows)} core, "
          f"{sum(r['decision'] == 'reject' for r in rows)} rejected")


if __name__ == "__main__":
    {"build": build, "review": review}[sys.argv[1]](sys.argv[2])
