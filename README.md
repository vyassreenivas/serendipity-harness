# A literature-to-coding harness for qualitative research

Prototype submitted with the proposal *Theory at scale, judgment at the
margins: an auditable harness for abductive coding with people and AI*
(Vyas Sreenivas and Ravi S. Kudesia), Organization Science special issue
"AI-Assisted Frontiers in Organizational Science". Draft, 23 October 2026.

The harness turns a research question and a set of papers into a codebook,
has people and a model code interviews with it on the same worksheet, and
records every step. It works in three boxes: build the codebook, code the
interviews, analyse. The worked example is serendipity in founder interviews
from Starter Story.

## Start here

| Open this | What you see |
|---|---|
| `harness_v2/docs/codebook/codebook_trail.html` | How the codebook was built: each sub-question, group and core code, with the paper sentences that state it; each paper and what it says; the definitions and anomaly codes |
| `harness_v2/docs/codebook/demo/demo_coding_page.html` | The coding page, on a made-up interview. Start an episode, tick codes, and watch which definitions of serendipity it meets |
| `harness_v2/docs/codebook/codebook_simple.docx` | The short codebook coders use |
| `harness_v2/docs/technical_document.docx` | The technical appendix |
| `harness_v2/docs/proposal/proposal.docx` | The proposal |

The HTML pages are single files and open in any browser, with no server.

## What is in this repository

| Path | What it is |
|---|---|
| `harness/` | The engine (version 1): one Python file per stage, from papers to candidate codes to a draft codebook, then interview segments, model coding and agreement. See `harness/README.md`. |
| `harness/prompts/` | The exact instructions given to the model at each stage |
| `harness/codebook/` | Decisions made after the draft: papers read later, anomaly codes, definitions of serendipity, the evidence sentence chosen for each core code, paper details |
| `harness/runs/` | Records of the two codebook runs: setup, paper inventory with file fingerprints, every candidate code with the passages it cites, the draft, the log |
| `harness_v2/stage1_question/` | Stage 1: the research question, sub-questions and analysis groups, with sources |
| `harness_v2/docs/codebook/` | Codebook tools and outputs: the review workbook, trail page, short codebook, code-to-paper map, coding page |
| `harness_v2/docs/source/` | Source of the technical appendix and its figures |
| `harness_v2/docs/proposal/` | Source of the proposal |

## Rebuild the codebook outputs (no papers needed)

Needs Python 3.11 or later.

```bash
pip install -r requirements.txt
cd harness_v2/docs/codebook
python trail.py codebook_review.xlsx codebook_trail.html
python codebook_simple.py codebook_review.xlsx codebook_simple.json
python paper_map.py codebook_review.xlsx codebook_paper_map.xlsx
python coding_page.py codebook_review.xlsx demo/demo_interview.jsonl demo/demo_coding_page.html --case-no 000
```

The Word files are built with Node and the `docx` package (version 9):

```bash
node codebook_simple.js codebook_simple.json codebook_simple.docx
```

## Rerun from the papers (needs your own copies)

The engine reads the PDFs named in `harness/project.toml` and
`harness/runs/*/inventory.json`, which records each file's fingerprint so a
rerun can be checked against ours. Stages that call a model need an API key
in `ANTHROPIC_API_KEY`, or a model on your own computer named in
`project.toml`.

```bash
cd harness
python -m serendipity_harness            # lists every stage
python -m serendipity_harness papers     # page text and numbered passages
```

## What is not here, and why

- **Papers**: no PDFs, page text or passages; they are copyrighted. The
  repository holds file fingerprints and passage numbers, so anyone with the
  papers can find every cited passage.
- **Interviews**: no Starter Story text, coded interviews, interview segments,
  saved model calls or model coding notes; the interviews are proprietary.
  The demo interview is invented.
- **Quotes we do keep**: the evidence for each code is one sentence per paper,
  with its page and link (trail page, review workbook, `evidence_picks.json`,
  `definitions.json`).

Rebuilt without the papers, the outputs match ours except for a few spacing
repairs that use the papers' own words.
