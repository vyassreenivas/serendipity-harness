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

### Short codebook (for coders and co-authors)

`codebook_simple.docx` is the codebook as coders read it: a one-page guide,
then for each group its question and a table of its core codes (code, code it
when, made-up example, not when, number of papers that state it), with the
group's anomaly code last. It is built from the workbook, so it follows every
edit:

    python codebook_simple.py codebook_review.xlsx codebook_simple.json
    node codebook_simple.js codebook_simple.json codebook_simple.docx

## Codebook trail and definitions

`python trail.py codebook_review.xlsx codebook_trail.html` writes one page that
shows how the codebook was built: sub-question, group, core code and the paper
sentences that state each code, plus a By paper view. A code or paper with no
such sentence is left out. Definitions of serendipity (Busch, Dew, Walpole)
live in `harness/codebook/definitions.json`: each is a rule over core codes,
with the papers' own sentences. Coders never tick them; the coding page shows
which definitions an episode meets and exports one yes/no column per rule.
