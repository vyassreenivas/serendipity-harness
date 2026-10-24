"""Command line: python -m serendipity_harness <stage>

Every command starts a new run folder.

  question     check the research question, sub-questions and chosen papers
               in question/: every paper, passage, page and quotation
  papers       hash the papers, save page text, cut passages, check the
               codebook's quotations
  codebook     read each paper for candidate codes, then synthesise them into
               a draft codebook for the researchers to review
               (calls an AI model; costs money)
  candidates   read for candidate codes only the papers the current draft has
               not read yet; the draft is left as it is (calls an AI model)
  freeze       turn the researchers' completed review sheet into a numbered
               codebook
  transcripts  list the interviews and cut them into identified segments
  toy          write fictional counterparts for a sample of interviews
               (calls an AI model; costs money)
  kit          write reading copies, the core-code list and blank worksheets
               for the human coders
  compare      report agreement between the completed worksheets in coding/
  code         the model codes interviews on the same worksheet
               (calls an AI model; costs money)
  all          papers and transcripts
"""
import json
import sys

from . import coding, inventory, passages, transcripts, verify
from .runlog import HARNESS, Run


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage not in ("all", "question", "papers", "codebook", "freeze", "candidates", "transcripts", "toy", "kit", "compare", "code"):
        raise SystemExit(__doc__)

    run = Run.create()
    print(f"run folder: {run.dir.relative_to(HARNESS.parent)}")

    if stage in ("all", "question", "papers", "codebook", "candidates"):
        papers = inventory.build(run)
        flagged = [p for p in papers if p["low_text_pages"] or p["error"]]
        print(f"inventory: {len(papers)} papers, {sum(p['pages'] for p in papers)} pages, "
              f"{len(flagged)} papers with pages to check by eye")
        print(f"passages: {passages.build(run)}")
    if stage in ("all", "papers"):
        print("quote check: " + json.dumps(verify.build(run)["by_level"]))
    if stage in ("all", "question"):
        from . import question
        q = question.build(run)
        print(f"question: status {q['question_status']}; {q['rows']} rows, {q['papers']} papers, "
              f"{q['rows_with_problems']} rows with problems; quotations {json.dumps(q['quote_match'])}")
        for sq, c in q["sub_questions"].items():
            print(f"  {sq}: {c['chosen']} chosen, {c['suggested']} suggested")
        for c in q["checked"]:
            for problem in c["problems"]:
                print(f"  line {c['line']} ({c['sub_question']}, {c['paper_file'][:40]}): {problem}")
        for paper, problem in q["paper_problems"].items():
            print(f"  {paper[:50]}: {problem}")
    if stage == "codebook":
        from . import extract, synthesize  # imported here so other stages run without pydantic
        print("candidate codes: " + json.dumps(extract.build(run)))
        print("draft codebook: " + json.dumps(synthesize.build(run)))
    if stage == "candidates":
        from . import extract
        print("candidate codes (papers new since the draft): " + json.dumps(extract.build(run, only_new=True)))
    if stage == "freeze":
        from . import freeze
        print("codebook: " + json.dumps(freeze.build(run)))
    if stage in ("all", "transcripts", "toy", "kit", "compare", "code"):
        cases = transcripts.build(run)
        print(f"transcripts: {len(cases)} interviews, {sum(c['segments'] for c in cases)} segments, "
              f"{sum(c['words'] for c in cases)} words, {sum(1 for c in cases if c['error'])} missing")
    if stage == "kit":
        print("coding kit: " + json.dumps(coding.kit(run)))
    if stage == "compare":
        report = coding.compare(run)
        for name, info in report["coders"].items():
            print(f"{name}: {info['cases_coded']} interviews, {info['episodes']} episodes, "
                  f"{len(info['problems'])} problems")
        for pair, result in report["pairs"].items():
            print(pair + ": " + json.dumps({k: result[k] for k in
                  ("cases_coded_by_both", "case_verdict_narrow", "case_verdict_broad", "episodes")}))
    if stage == "code":
        from . import model_coding
        print("model coding: " + json.dumps(model_coding.build(run)))
    if stage == "toy":
        from . import toy  # imported here so the other stages run without the model library
        for row in toy.build(run):
            d = row.get("distance", {})
            print(f"{row['toy_id']}: {row['status']}; events {row.get('events', '-')}; "
                  f"words {d.get('source_words', '-')} -> {d.get('toy_words', '-')}; "
                  f"flags {row.get('flags', '-')}")


if __name__ == "__main__":
    main()
