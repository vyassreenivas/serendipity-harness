# A literature-to-coding harness for qualitative research

Prototype submitted with our proposal to the Organization Science special issue
"AI-Assisted Frontiers in Organizational Science" (Vyas Sreenivas and Ravi S.
Kudesia).

The harness turns a research question and a set of papers into a codebook, has
people and a model code the same interviews with it, keeps what the codebook
misses as anomalies, and grows the codebook round by round from those
anomalies. Every step is recorded so it can be checked and rerun. The worked
example is serendipity in founder interviews from Starter Story.

## Start here

| Open this | What you see |
|---|---|
| `package/1_research_question.docx` | The research question and its six sub-questions |
| `package/2_paper_list.docx` | The 14 papers that together state every code, and why each matters |
| `package/3_codebook.docx` | Codebook version 1.0: 36 level-1 codes in eight groups, and 11 level-2 items worked out from them |
| `package/4_technical_document.html` | The technical appendix: the method, step by step, and where each step stands |
| `package/5_code_sources.html` | Every code with the papers and sentences that state it |
| `package/6_codebook_progression.html` | How the codebook grows: each version side by side, with the codes and papers each one adds |
| `harness_v2/docs/codebook/demo/demo_coding_page.html` | The coding page on an invented interview: name a story, tick codes, and see which definitions of serendipity it meets |
| `harness_v2/docs/technical_v2/process.html` | Every step: who does it (us, the model or a program), its files and what it records |

The HTML pages are single files and open in any browser, with no server.

## What is in this repository

| Path | What it is |
|---|---|
| `harness/serendipity_harness/` | The program, one file per step: papers, candidate codes, draft codebook, freeze, interview segments, model coding, checks, comparison of coders, anomaly log, codebook progression |
| `harness/prompts/` | The exact instructions given to the model at each step |
| `harness/codebook/` | Codebook version 1.0 (`codebook_v1.0.json`), the decisions behind it, and the anomaly log |
| `harness/runs/` | Records of the runs that built codebook 1.0: setup, paper inventory with file fingerprints, every candidate code with the passages it cites, the draft and the log |
| `harness/project.toml` | The study's setup: question, construct, inputs, groups, models. Edit this to use the harness on another question |
| `harness_v2/docs/codebook/` | Tools that turn the codebook into the documents above, and the coding page |
| `harness_v2/docs/technical_v2/` | Source of the technical appendix and its figures |
| `harness_v2/build_submission.py` | Rebuilds this repository from our working repositories and checks it holds no interview text or papers |
| `MANIFEST.json` | Every file with its fingerprint, and the commits it was built from |

## Run it

Needs Python 3.11 or later.

```bash
pip install -r requirements.txt
cd harness
python -m serendipity_harness            # lists the main steps
```

The steps of a coding round each take a round's folder:

```bash
python -m serendipity_harness.coded_pages ROUND_DIR PAGES_DIR   # check the model's coding; one page per interview
python -m serendipity_harness.compare ROUND_DIR                 # compare the coders, story by story
python -m serendipity_harness.anomaly_log add ROUND_DIR --round 1
python -m serendipity_harness.progression OUT_DIR               # how the codebook grew
```

Steps that call a model need an API key in `ANTHROPIC_API_KEY`, or a model on
your own computer named in `project.toml`.

The codebook documents rebuild from the review workbook, without the papers:

```bash
cd harness_v2/docs/codebook
python code_sources.py codebook_review.xlsx code_sources.html
python trail.py codebook_review.xlsx codebook_trail.html
python coding_page.py codebook_review.xlsx demo/demo_interview.jsonl demo/demo_coding_page.html --case-no 000
```

Rebuilt without the papers, they match ours except for the build date and a few
word-spacing repairs that need the papers' own text (for example "under way"
where the PDF text has "underway").

## Where it stands (1 November 2026)

- Codebook version 1.0 is built from 100 works and frozen.
- Round 1: the model has coded 25 interviews drawn at random, in 111 stories.
  It left 35 anomalies, grouped into 14 themes in `harness/codebook/anomaly_log.csv`.
- Our own coding of round 1, codebook version 2.0 and round 2 are in progress.

## What is not here, and why

- **Papers**: no PDFs, page text or passages; they are copyrighted. The
  records keep file fingerprints and passage numbers, so anyone with the
  papers can find every cited passage. Each code keeps one short sentence per
  paper, with its page.
- **Interviews**: no Starter Story text, interview segments, coded interviews
  or saved model calls; the interviews are proprietary. The anomaly log names
  interviews by id and segment number only. The demo interview is invented.
  The build checks that no run of 10 words in this repository also occurs in
  any Starter Story interview.
