"""Stage A0 check: the research question, the sub-questions and the chosen papers.

The researchers write question/research_question.md and question/papers.csv.
This stage does not change them. It checks that every row of papers.csv can be
traced: the paper is in the inventory, the sub-question exists, the cited
passages exist in that paper and lie on the pages given, and the quotation is
in one of the cited passages. It also reports which sub-questions have papers.
No model is involved.

Quotation match levels are those of the quotation check (verify.py):
exact, typographic, case, loose, not_found. "loose" usually means the PDF's
extracted text splits a word ("bene ficial"); the reader should look at it.
"""
import csv
import re

from .runlog import HARNESS, Run, sha256
from .verify import loose, typographic

QUESTION_DIR = HARNESS / "question"
FILES = ["research_question.md", "papers.csv", "search_log.md", "README.md"]
ROLES = {"main", "also"}
STATUSES = {"suggested", "chosen", "dropped"}
COLUMNS = ["sub_question", "paper_file", "role", "what_it_offers", "evidence_passages",
           "evidence_pages", "evidence_quote", "how_found", "chosen_by", "date_added", "status"]
LONG_QUOTE = 30  # words


def fingerprints() -> dict:
    """SHA-256 of each file in question/, so a run records exactly which version it used."""
    return {name: sha256(QUESTION_DIR / name) for name in FILES if (QUESTION_DIR / name).exists()}


def match_level(quote: str, text: str) -> str:
    if quote in text:
        return "exact"
    if typographic(quote) in typographic(text):
        return "typographic"
    if typographic(quote).lower() in typographic(text).lower():
        return "case"
    if loose(quote) and loose(quote) in loose(text):
        return "loose"
    return "not_found"


def split(field: str) -> list[str]:
    return [x.strip() for x in field.split(";") if x.strip()]


def build(run: Run) -> dict:
    question_text = (QUESTION_DIR / "research_question.md").read_text(encoding="utf-8")
    status = re.search(r"^Status:\s*(\w+)", question_text, re.M)
    sub_questions = dict(re.findall(r"^### (SQ\d+)\.\s*(.+)$", question_text, re.M))

    inventory = {r["file"].split("/")[-1]: r for r in run.read_json("inventory.json")}
    passages_cache = {}

    def passages_of(paper_id):
        if paper_id not in passages_cache:
            import json
            path = run.dir / "passages" / f"{paper_id}.jsonl"
            rows = [json.loads(line) for line in open(path, encoding="utf-8")] if path.exists() else []
            passages_cache[paper_id] = {p["passage_id"].split(":", 1)[1]: p for p in rows}
        return passages_cache[paper_id]

    with open(QUESTION_DIR / "papers.csv", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing_columns = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        rows = list(reader)

    checked, mains = [], {}
    for n, row in enumerate(rows, start=2):  # line 1 is the header
        problems = []
        paper = inventory.get(row["paper_file"])
        if row["sub_question"] not in sub_questions:
            problems.append(f"sub-question {row['sub_question']!r} is not in research_question.md")
        if row["role"] not in ROLES:
            problems.append(f"role {row['role']!r} is not main or also")
        if row["status"] not in STATUSES:
            problems.append(f"status {row['status']!r} is not suggested, chosen or dropped")
        if not paper:
            problems.append("paper file is not in the papers folder")
        ids, pages = split(row["evidence_passages"]), split(row["evidence_pages"])
        if not ids:
            problems.append("no evidence passages")
        level, found_in = "not_checked", None
        if paper:
            known = passages_of(paper["paper_id"])
            absent = [i for i in ids if i not in known]
            if absent:
                problems.append("passages not in this paper: " + ", ".join(absent))
            on_pages = {str(known[i]["pdf_page"]) for i in ids if i in known}
            if set(pages) != on_pages:
                problems.append(f"pages given {sorted(pages)} differ from the pages of the "
                                f"cited passages {sorted(on_pages)}")
            quote = row["evidence_quote"].strip()
            if not quote:
                problems.append("no quotation")
            else:
                order = ["exact", "typographic", "case", "loose", "not_found"]
                best = "not_found"
                for i in ids:
                    if i in known:
                        lv = match_level(quote, known[i]["text"])
                        if order.index(lv) < order.index(best):
                            best, found_in = lv, i
                level = best
                if level == "not_found":
                    problems.append("quotation is not in any cited passage")
                if len(quote.split()) > LONG_QUOTE:
                    problems.append(f"quotation is longer than {LONG_QUOTE} words")
        if row["status"] != "dropped" and row["role"] == "main":
            mains.setdefault(row["paper_file"], []).append(n)
        checked.append({"line": n, "sub_question": row["sub_question"], "paper_file": row["paper_file"],
                        "role": row["role"], "status": row["status"],
                        "quote_match": level, "quote_found_in": found_in, "problems": problems})

    papers_listed = sorted({r["paper_file"] for r in rows if r["status"] != "dropped"})
    paper_problems = {p: "no row marked main" for p in papers_listed if p not in mains}
    paper_problems.update({p: f"more than one row marked main (lines {lines})"
                           for p, lines in mains.items() if len(lines) > 1})
    coverage = {sq: {"question": q,
                     "chosen": sum(1 for r in rows if r["sub_question"] == sq and r["status"] == "chosen"),
                     "suggested": sum(1 for r in rows if r["sub_question"] == sq and r["status"] == "suggested")}
                for sq, q in sub_questions.items()}

    report = {"question_status": status.group(1) if status else None,
              "files": fingerprints(),
              "missing_columns": missing_columns,
              "rows": len(rows), "papers": len(papers_listed),
              "rows_with_problems": sum(1 for c in checked if c["problems"]),
              "quote_match": {lv: sum(1 for c in checked if c["quote_match"] == lv)
                              for lv in ["exact", "typographic", "case", "loose", "not_found", "not_checked"]},
              "paper_problems": paper_problems,
              "sub_questions": coverage,
              "checked": checked}
    run.write_json("question_check.json", report)
    run.log("question_checked", **{k: report[k] for k in
                                   ("question_status", "files", "rows", "papers", "rows_with_problems", "quote_match")})
    return report
