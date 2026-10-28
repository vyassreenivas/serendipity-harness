# Pilot codebook (readable version)

`export.py` reads the review sheet (`review.csv` once the researchers have
saved it, otherwise `review_suggested.csv`), the draft codebook and the source
metadata from the version 1 harness, and writes `codebook.json`.
`build_codebook.js` turns that into `codebook_pilot.docx`: the 11 groups in
sub-question order, each core code in plain words. Under each code, the five papers with the most supporting passages are quoted: one sentence each, chosen by fixed code (`best_sentence` in export.py: most distinctive words shared with the code's draft wording; 8 to 45 words; boilerplate and citation lists excluded), copied from the extracted PDF text with its page. The rest are listed with links.

```bash
python export.py codebook.json
node build_codebook.js codebook.json codebook_pilot.docx
```

Source links: 79 of the 86 cited files have a DOI (read from the PDF where it
states one, otherwise matched on Crossref by title, first author and year).
The details are in `harness/codebook/paper_metadata.json`.

## Review workbook

`workbook.py build codebook_review.xlsx` writes the workbook the researchers
review in. Its first tab, **Coder view**, is the codebook as coders use it:
one short line per core code under its group (code, code it when, example, not
when, papers), read by formula from the Codebook sheet, so it never goes out of
step. Word limits keep it short (label 5 words, code it when 20, example 20,
not when 15); wording over a limit is shaded on the Codebook sheet, and the
build prints how many codes are over. The **Codebook** sheet holds only the core codes and the 10 anomaly
codes: their wording and reasons are edited there. The **All codes** sheet
holds every drafted code: its Status (core, reference or reject) is edited
there, and wording only for reference codes. Groups (live counts), Evidence
(one row per code and paper, with the best sentence, page and link) and
Sources complete it. Rebuilding an existing workbook keeps every edit (the old
file is kept as `.bak`) and moves codes onto or off the Codebook sheet to match
their Status.

`workbook.py review codebook_review.xlsx` works out accept or revise by
comparing the wording with the draft, checks the entries, and writes
`harness/codebook/review.csv` for `freeze`; it never overwrites an existing
file. Tested: an unchanged workbook reproduces `review_suggested.csv` exactly;
a promoted code moves onto the Codebook sheet; Codebook edits survive a
rebuild. `metadata.py` adds source details for any cited paper not yet in
`harness/codebook/paper_metadata.json`. Building needs `openpyxl`.

### Papers read after the draft

Six papers were added on 21 Oct 2026 and read in a Claude Code session with
the harness's own prompt and passage checks (run `20261021-003947`;
`extract.from_inapp`). `harness/codebook/added_papers.json` records each
candidate as a match to an existing code (`same idea` or `close`) or as a new
reference code; `inapp_mapping_20261021.csv` is the same table to read. The
workbook, `review` and `freeze` all read this file, so the draft itself is left
as it is. Evidence sentences for core-code matches were chosen by reading and
sit in `evidence_picks.json` (`source: added_papers.json`). A rerun of the
whole chain through the API will replace this record.

### Interactive codebook

`python codebook_page.py codebook_review.xlsx` writes `codebook.html` from the
workbook: the coder view on the left (11 groups, one line per code) and, for
the selected code, its full entry and the evidence sentence from each paper,
with page and link. A switch shows reference codes too. Coders can tick the
codes that apply to an episode and copy their IDs. Rebuild it after editing
the workbook. It holds codes, our wording and one-sentence quotes from papers;
no interview text. A private copy is published at
https://claude.ai/artifact/R234uHoz5waP15ZiwbLipt (share it from its page).

### Codebook document (for readers and reviewers)

`codebook_simple.docx` is the codebook as a reader sees it, not a coding guide:
how it is organised (sub-questions, groups, number of codes), the two levels,
then for each group a table of its codes numbered by group (2.3 is the third
code of group 2), each with what it captures (the workbook's Description) and
the first three papers that state it. Each group's anomaly code comes last.
Level 2 gives each definition, rival, type and judgment with its rule over the
numbered level-1 codes. The coders' instructions are on the coding page. It is
built from the workbook, so it follows every edit:

    python codebook_simple.py codebook_review.xlsx codebook_simple.json
    node codebook_simple.js codebook_simple.json codebook_simple.docx

### Codebook sources

`code_sources.html` is one simple table: for each code, its group, its number
and label, and every paper that states it with the sentence chosen by reading
and its page. Level-2 items follow with their rules. Links that only come close
are marked "leans on it":

    python code_sources.py codebook_review.xlsx code_sources.html

### Research question and sub-questions

`questions.docx` gives the research question, its six sub-questions, the groups
the papers were read for, and the groups coders answer. The wording is in
`questions.json`:

    node questions.js questions.json questions.docx

### Papers behind the codebook

`paper_list.docx` lists every work the model read for candidate codes, with
the level-1 codes and level-2 items each supports (numbered as in the codebook
document) and one line on why it is there (`paper_why.json`), then the works
read that support none. A link counts only where a sentence chosen by reading
states the code. It holds references and code labels only:

    python paper_list.py codebook_review.xlsx paper_list.json
    node paper_list.js paper_list.json paper_list.docx
    node paper_list.js paper_list.json paper_list_core.docx core

`paper_list_core.docx` lists only the core papers (`harness/codebook/core_papers.json`):
the smallest set of the works read that states every code, each code by two
works wherever two state it, with the four works the definitions and types come
from. For each: its citation, and what it argues and what it gives the codebook under each
sub-question it serves, named in brackets: the ones where it states two or more codes,
plus those of the codes it is in the core for. The build checks that the line
names exactly the sub-questions listed. `paper_list.py` checks on every build that the core papers
still state every code and prints any code left uncovered.

## Codebook version 1.0: two levels

The codebook was frozen as version 1.0 on 25 October 2026
(`harness/codebook/codebook_v1.0.json`, written by `python -m serendipity_harness freeze`).
It has two levels, set in `harness/codebook/levels.json`:

- Level 1 is what coders tick: 36 codes in 8 groups, including a pick-one
  search-state question, plus one anomaly code per group and ANO-NEW.
- Level 2 is worked out after coding: three definitions (Busch, Dew, Walpole),
  two rival explanations (pure luck; targeted search or a plan), four types
  (after Yaqub 2018), and two judgments the researchers decide.

`levels.py` reads the levels for every page, so the short codebook, coding page
and trail always agree:

```bash
python codebook_simple.py codebook_review.xlsx codebook_simple.json
node codebook_simple.js codebook_simple.json codebook_simple.docx
python trail.py codebook_review.xlsx codebook_trail.html
python coding_page.py codebook_review.xlsx SEGMENTS.jsonl OUT.html --case-no 001
```

The prompts that produce a codebook of this shape from a question,
sub-questions and papers are in `drafts/prompt_draft2.md`.
