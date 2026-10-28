# Harness, version 2: documents and codebook tools

The program is in `../harness/`. This folder holds what turns its records into
documents people read, and the technical appendix.

| Path | What it is |
|---|---|
| `docs/technical_v2/` | The technical appendix (`technical_draft.md`), the process page and the figures, all built from `process.json` by `views.py` and `figures.py` |
| `docs/codebook/` | The codebook review workbook, and the tools that build the research question, paper list, short codebook, code sources, codebook trail and coding pages from it. See its README. |
| `docs/codebook/demo/` | The coding page on an invented interview |
| `build_submission.py` | Rebuilds the submission repository and checks it for interview text and papers |
| `submission_README.md` | The submission repository's front page |
| `outputs/` | Kept local: anything that holds interview text |
