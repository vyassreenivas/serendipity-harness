# Serendipity research harness

A small, readable pipeline that builds a qualitative codebook from a set of
papers, has people and a model apply it to interviews on the same worksheet,
and records every step so it can be checked and rerun.

It starts from four things you supply: a folder of papers, a construct, a
research question, and a folder of interviews. All four are named in
`project.toml`.

This is version 1 of the harness, the engine. The method is described in
`../harness_v2/docs/technical_document.docx`.

## Stages

| Stage | Command | Who does the work | Built |
|---|---|---|---|
| Research question, sub-questions, chosen papers with evidence (`question/`) | `question` checks them | Researchers; checked by fixed code | yes; question in draft; 4 papers entered |
| Paper inventory, page text, passages | `papers` | Fixed code | yes |
| Candidate codes from each paper | `codebook` | Model, checked by fixed code | yes; run on 107 papers |
| Draft codebook from the candidates | `codebook` | Model, checked by fixed code | yes; 360 draft codes |
| Researcher review of the draft | (a spreadsheet) | Researchers | sheet is produced; not yet filled in |
| Numbered codebook from the review | `freeze` | Fixed code | yes; tested on a made-up review only |
| Quotation check | `papers` | Fixed code | yes |
| Interview inventory and numbered paragraphs | `transcripts` | Fixed code | yes |
| Coding kit for human coders | `kit` | Fixed code | yes |
| Agreement, candidate codes, code use | `compare` | Fixed code | yes; tested on made-up data only |
| Model coding of interviews | `code` | Model, checked by fixed code | yes; tried on 5 interviews with a small local model |
| Fictional counterparts of interviews | `toy` | Model, checked by fixed code | trial run on 5; revision not yet run |

## Run it

Needs Python 3.11 or later.

```bash
pip install -r requirements.txt
```

```bash
python -m serendipity_harness papers
```

`python -m serendipity_harness` lists every command. The commands marked
"calls an AI model" cost money and need an API key in `ANTHROPIC_API_KEY`,
unless `project.toml` points that stage at a model running on your machine.

## What is in this folder

| Path | What it is |
|---|---|
| `project.toml` | The run setup: question, construct, inputs, codebook groups, models. Edit this to use the harness on another topic. |
| `methods_papers.txt` | Papers in the papers folder that are about method and are not read for codes. |
| `prompts/` | The exact instructions given to the model at each stage. |
| `serendipity_harness/` | The code, one file per stage. |
| `codebook/` | Decisions made after the draft: added papers, anomaly codes, definitions, evidence picks, paper details, the change log. |
| `runs/` | One folder per run, named by date and time. Never overwritten. |

The papers and interviews are not in this folder and are not published. The
harness expects them beside it, at the paths given in `project.toml`.

## What a run produces

- `project.toml`: the setup used for this run
- `inventory.json`: one record per paper (ID, file, fingerprint, page count, flagged pages)
- `candidates/`: one file per paper with its candidate codes and the passages cited
- `codebook_draft.json`, `codebook_review.csv`: the draft codebook and the sheet the researchers decide on
- `quote_check.csv`: one row per code with match level and PDF page
- `kit/`: core codes with sources, blank worksheets, the change log
- `agreement.json`: agreement between coders, candidate codes proposed, code use
- `log.jsonl`: one line per step, with counts, versions and file fingerprints

Kept on your machine and out of git, because they copy the papers or the
interviews: page text, passages, interview paragraphs, reading copies, saved
model calls, and model coding output.
