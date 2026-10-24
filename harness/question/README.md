# Stage A0: the question and the papers

This is the first stage of the harness, and it is done by the researchers.
It fixes what the study asks and which papers the codebook will be built
from, before any model reads anything.

## The files

| File | What it holds | Who writes it |
|---|---|---|
| `research_question.md` | The central question and the sub-questions (SQ1, SQ2, ...). For each sub-question: what we look for in an interview, and which codebook groups it feeds | Researchers |
| `papers.csv` | One row for each paper and each sub-question it serves, with the evidence from the paper | Researchers |
| `search_log.md` | The searches that found papers, as typed, with dates | Researchers |

The papers themselves are in `../papers/pdf/`, outside this repository,
because they are copyrighted. `papers.csv` names each by its file name there.

## `papers.csv` columns

One row is one paper serving one sub-question. A paper that speaks to five
sub-questions has five rows, each with its own evidence. Rows are kept in
sub-question order, so the file reads as: for each sub-question, the papers
that answer it and what each one says.

| Column | What goes in it |
|---|---|
| `sub_question` | SQ1, SQ2, ... as defined in `research_question.md` |
| `paper_file` | The file name in `papers/pdf/`, exactly |
| `role` | `main` for the one sub-question the paper is chosen mainly for (a paper usually has one main message), `also` for the others. Each paper has exactly one `main` row |
| `what_it_offers` | One sentence, in the researcher's words: what the paper says that bears on this sub-question |
| `evidence_passages` | The passage numbers in the paper that state it, such as `p005:01;p008:02` (PDF page 5, first passage). Passage numbers come from the harness's passage files, so anyone can open the exact text |
| `evidence_pages` | The PDF pages of those passages, such as `5;8`. The check confirms they match |
| `evidence_quote` | A short quotation, copied word for word from one of those passages, under 30 words |
| `how_found` | Database search (see the search log), followed a reference (from which paper), recommended (by whom), or already known |
| `chosen_by` | Initials of the researcher who chose it |
| `date_added` | YYYY-MM-DD |
| `status` | `suggested` (proposed, for example by a model, not yet decided), `chosen`, or `dropped` (keep the row; say why in `what_it_offers`) |

## The check

```bash
.venv/bin/python -m serendipity_harness question
```

This inventories the papers, cuts the passages, then checks every row of
`papers.csv` without changing it: the paper is in the papers folder, the
sub-question exists, the cited passages exist in that paper, the pages match,
the quotation is in one of the cited passages, and each paper has one `main`
row. It reports how many papers each sub-question has, chosen and suggested,
and writes `question_check.json` in the run folder. Quotations are matched
at the same levels as the codebook's quotation check; `loose` usually means
the PDF's extracted text splits a word, and is worth a look.

Every run of the harness, whatever the command, records a fingerprint of the
files in this folder in its log, so each result can be traced to the exact
version of the question and paper list it used.

## Rules

1. **People decide.** A model may suggest a question's wording, a paper, or a
   sub-question tag; such rows are marked `suggested`. Only a researcher
   changes a row to `chosen`.
2. **Decide before reading.** The question, sub-questions and chosen papers
   are committed before the harness reads the papers for codes. A later
   change is a new commit whose message says what changed and why.
3. **Every sub-question needs papers.** A sub-question with few papers is a
   gap to fill by searching, not by stretching other papers.
4. **Nothing is deleted.** A dropped paper keeps its row, with the reason.

## How later stages use this

- Stage A1 inventories every file in `papers/pdf/`; `papers.csv` says which
  of them were chosen and why.
- In stage A2 a model reads each chosen paper for candidate codes. The plan
  is to ask about the sub-questions the paper is tagged with, one at a time,
  rather than about everything at once.
- In the review (A5), a code is kept only if it helps answer a sub-question.

Not yet built: stages A2 and later do not yet use the sub-questions; they
still read every paper not listed in `methods_papers.txt`, and take the
question from `project.toml`.

## State on 16 October 2026

- `research_question.md`: draft, to be rewritten and agreed by Vyas and Ravi.
- `papers.csv`: the four definitional papers, 24 rows covering all six
  sub-questions, all `suggested`. The evidence was taken from the passages
  the models cited when reading these papers and checked by the harness
  (run `20261016-143258`: no problems; 22 quotations exact or typographic,
  2 loose). "How found" and "chosen by" are left for the researchers. The
  other 104 serendipity papers are not yet listed.
- `search_log.md`: empty.
