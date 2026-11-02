# A literature-to-coding harness for qualitative research

Prototype submitted with our proposal to the Organization Science special issue
"AI-Enabled Frontiers in Organizational Science". Vyas Sreenivas and Ravi S.
Kudesia, 1 November 2026.

> **Editors and reviewers: start with [`1_package/`](1_package).** It holds
> everything to read. You do not need the other folders.
>
> 1. **Download the repository:** the green **Code** button above, then **Download ZIP**. Unzip it.
> 2. **Read the technical appendix:** `1_package/1_technical_document.docx`.
> 3. **Open the rounds in a browser:** `1_package/rounds/index.html` links every codebook version, every round and the coded interviews.
>
> GitHub shows `.html` files as code, so open them from the download.

The harness helps researchers code a large collection of texts, such as
interviews, using ideas from published research. It builds a codebook from
papers, has an AI model code the texts in rounds of 25, keeps what the codebook
cannot explain as anomalies, and grows the codebook from the papers that explain
them. Anomalies that no paper explains are kept for study at the end, where new
theory can come from. Researchers make every research decision; the model reads
and suggests; a plain program checks its work. Every step is recorded so it can be
checked and rerun.

Our worked example is serendipity in founder interviews from Starter Story.

## What is in `1_package/`

| Open this | What you see |
|---|---|
| [`1_technical_document.docx`](1_package/1_technical_document.docx) | The technical appendix: what the harness does, the four stages, and how to use it on another question |
| [`2_figures.pptx`](1_package/2_figures.pptx) | The appendix's four figures, editable |
| [`3_research_question.docx`](1_package/3_research_question.docx) | The research question and its sub-questions |
| [`4_codebook_progression.html`](1_package/4_codebook_progression.html) | Every code against every codebook version, 1.0 to 4.0 (draft), with where each came from |
| [`5_process.html`](1_package/5_process.html) | Every step, who does it (researchers, model or program), and what it records |
| [`rounds/index.html`](1_package/rounds/index.html) | The calibration rounds, in order: codebook 1.0, round 1, the paper search, codebook 2.0, how the codebook grew, round 2, codebook 3.0, round 3, and the coded interviews of each round |

**The coded interviews are confidential.** Starter Story owns the interviews.
`1_package/rounds/interviews_round1/`, `interviews_round2/` and `interviews_round3/`
hold each interview of the three rounds as coded, with names and personal details
replaced. They are here for the editors and reviewers only, while this repository
is private: please do not share them. Each round folder holds that round's new
interviews and the earlier ones it recoded. The raw interviews are not here.

## Who does what

The researchers make every research decision. The model reads and suggests. A
plain program checks the model's work.

| | Researchers | Model | Program |
|---|---|---|---|
| Question | Choose the research question, its sub-questions and groups | | |
| Papers | Choose the papers; read them | Read each paper in full; draft codes with the passages they rest on | Number every passage; check that each quoted passage is in its paper |
| Codebook | Decide every code: keep, change or drop | | Freeze each version; record every change and its reason |
| Coding | Code a sample of interviews by hand; compare with the model | Code each interview, giving a reason before each code | Check the coding; compare old with new, and ours with the model's |
| Anomalies | Group them; decide which become codes | Flag passages no code fits; search the papers for each group of anomalies | Log every anomaly and every search |
| Findings | Interpret and build theory | | Count codes; trace anomalies across versions |

Every code in versions 1.0 to 3.0 entered the codebook by a researcher's decision
and rests on a paper that states it. Version 4.0 is a draft still awaiting that
decision. The records of every decision are in `harness/codebook/`.

## The four stages, and where each lives

| Stage | What it does | Program | Records |
|---|---|---|---|
| 1. From research question to groups | Breaks the question into sub-questions and groups | `harness/serendipity_harness/question.py` | `harness/question/` |
| 2. From papers to codebook | The model reads each paper in full and drafts codes; researchers decide; every link to a paper is checked | `passages.py`, `extract.py`, `synthesize.py`, `freeze.py` | `harness/runs/`, `harness/codebook/codebook_v1.0.json` |
| 3. Coding rounds | Draws 25 interviews, has the model code them with reasons, compares codings, logs anomalies, writes the next codebook version | `rounds.py`, `model_coding.py`, `coded_pages.py`, `agreement.py`, `compare.py`, `anomaly_log.py`, `next_version.py` | `harness/codebook/` (versions, changes files, anomaly log, literature checks, agreement) |
| 4. Analysing the anomalies | Groups what no code fits and checks it against the literature | `anomaly_log.py` | `harness/codebook/anomaly_log.json`, `harness/codebook/literature_*.json` |

## What is in this repository

| Path | What it is |
|---|---|
| `harness/serendipity_harness/` | The program, one file per step |
| `harness/prompts/` | The exact instructions given to the model |
| `harness/project.toml` | The study's settings: question, groups, folders and models. Edit this to use the harness on another question |
| `harness/codebook/` | Codebook versions 1.0, 2.0, 3.0 and 4.0 (draft); the changes file that made each from the one before; the anomaly log with every search; the literature checks; agreement between rounds |
| `harness/runs/` | Records of the runs that built codebook 1.0: setup, paper list with file fingerprints, every candidate code with the passages it cites |
| `1_package/` | What editors and reviewers read (see above) |
| `documents/` | Supporting files: the sub-questions, the prompt that built codebook 1.0, the sources of the figures, and the script that builds this repository and checks it holds no interview text or papers |
| `MANIFEST.json` | Every file with its fingerprint, and the commits it was built from |

## Run it

### Quick start: rebuild our codebooks (5 minutes, no data or model needed)

Needs Python 3.11 or later and git.

```bash
git clone https://github.com/vyassreenivas/serendipity-harness.git
cd serendipity-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd harness
```

Rebuild codebook versions 2.0, 3.0 and 4.0 (draft), each from the version before and its changes file:

```bash
python -m serendipity_harness.next_version codebook/changes_v2.0.json
python -m serendipity_harness.next_version codebook/changes_v3.0.json
python -m serendipity_harness.next_version codebook/changes_v4.0_draft.json
git status
```

`git status` should report no changes: the rebuilt codebooks are identical to ours.

See every anomaly theme across the three rounds, and how the codebook grew:

```bash
python -m serendipity_harness.anomaly_log show
python -m serendipity_harness.progression ../progression_out
```

The second command writes `codebook_progression.html`; open it in a browser.

### What each part needs

| To do this | You need |
|---|---|
| Rebuild the codebooks; see the anomaly log and how the codebook grew | Nothing beyond this repository |
| Check every quote against its paper (`python -m serendipity_harness.evidence codebook/evidence_v3.0.json`) | The papers, as PDFs or text, which we cannot share; quotes from papers you lack show as MISSING |
| Build a codebook from papers (Stage 2) | Your papers, and an Anthropic API key or a local model |
| Code interviews in rounds (Stage 3) | Your texts, and an Anthropic API key or a local model |

`python -m serendipity_harness` lists the main stages. The steps of a coding round each take the round's folder:

```bash
python -m serendipity_harness.rounds WORK_DIR --codebook codebook/codebook_v3.0.json --draw 25 --seed SEED
python -m serendipity_harness.coded_pages WORK_DIR PAGES_DIR      # check the model's coding; one page per interview
python -m serendipity_harness.agreement WORK_A WORK_B OUT_CSV     # compare two codings of the same interviews
python -m serendipity_harness.anomaly_log add WORK_DIR --round N  # record the round's anomalies
```

Models are set in `harness/project.toml`: Claude through the Anthropic API (set
`ANTHROPIC_API_KEY`), or an open-weight model on your own computer through
Ollama. Every model call is saved, and a saved call is reused, so a run can be
replayed without the model.

## Using it on another question

Change four things and keep the rest: the settings in `harness/project.toml`; the
papers (PDFs); the texts to code (one text file each); and the opening lines of
`harness/prompts/coder.md`, which describe our study. Section 7 of the technical
appendix explains each.
