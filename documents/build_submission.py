"""Assemble the submission repository from the two working repositories.

Usage: python build_submission.py [TARGET]   (default: ../submission/serendipity-harness)

The target is a git repository. Everything in it except .git is removed and
rebuilt from what is committed in harness/ and harness_v2/ (as documents/), the codebook run
records, and the reviewer package, so the repository can be remade the same way
at any time. Nothing is committed: check the result, then commit in the target.

Then a privacy check: no PDFs, no paths that hold papers' text or interviews,
and no stretch of text shared with a Starter Story interview: a file fails if it
has three or more 10-word runs that also occur in one interview (about 12 words
in a row or more). Single runs are common phrases, such as "in the right place at
the right time" or the interviews' standard first question. The build fails if
the check finds anything. MANIFEST.json lists every file with its
fingerprint and the commits it was built from.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS, V2 = ROOT / "harness", ROOT / "harness_v2"
INTERVIEWS = ROOT / "outputs" / "starter_story_interviews_txt"

# Files committed in harness/ that are kept out: the first technical document and
# notes written for the episode design, which the current documents replace.
HARNESS_SKIP = ["docs/PRD.md", "docs/coding_instructions.md", "docs/technical_supplement.md",
                "docs/technical_document.docx", "docs/technical_document_source/*"]
# What goes in from harness_v2/, under the name documents/: only what the program
# and its records point to (the sub-questions, the prompt that built codebook 1.0),
# the sources of the figures and the process page, and this script. Drafts and
# working files stay out; what editors read goes in 1_package/.
DOCS = "documents"
V2_TAKE = ["build_submission.py", "docs/technical_v2/process.json", "docs/technical_v2/figures.py",
           "docs/technical_v2/figures_pptx.py", "docs/technical_v2/views.py",
           "docs/codebook/questions.json", "docs/codebook/drafts/prompt_draft2.md"]
V2_SKIP: list[str] = []
# The runs that built codebook 1.0: setup, paper inventory, candidate codes with the
# passages they cite, the draft and the log. Never page text, passages or calls.
RUNS = {"20261012-124904": ["project.toml", "inventory.json", "log.jsonl", "codebook_draft.json",
                            "codebook_review.csv", "candidates/*"],
        "20261021-003947": ["project.toml", "inventory.json", "log.jsonl", "candidates/*", "inapp/*"]}
# The reviewer package, numbered in reading order, each from the committed file it is built as.
PACKAGE = {"1_technical_document.docx": "docs/technical_v2/Technical_Documentation_V1.docx",
           "2_figures.pptx": "docs/technical_v2/technical_figures.pptx",
           "3_research_question.docx": "docs/codebook/questions.docx",
           "4_codebook_progression.html": "docs/codebook/codebook_progression.html",
    "5_process.html": "docs/technical_v2/process.html"}
PACKAGE_DIR = "1_package"
# The pages of the calibration rounds, under their own names so their links work. The coded
# interviews they link to are not here: they go to reviewers only, in a confidential file.
ROUND_PAGES = ["1_codebook_v1.html", "2_round1_coding.html", "3_paper_search.html", "4_codebook_v2.html",
               "5_progression.html", "6_round2_coding.html", "7_codebook_v3.html", "8_round3_coding.html"]

FORBIDDEN_PARTS = {"pages", "passages", "segments", "calls", "model_coding", "interviews_25", "coders",
                   "replies", "checked", "outputs", "coded", "to_code"}
TEXT = {".md", ".html", ".json", ".jsonl", ".csv", ".txt", ".py", ".js", ".toml"}
RUN = 10  # words
SHARED = 3  # runs shared with one interview before a file is flagged


def tracked(repo: Path) -> list[str]:
    return subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True).stdout.split()


def head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()


def match(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def assemble(target: Path) -> None:
    for p in target.iterdir():
        if p.name != ".git":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    for f in tracked(HARNESS):
        if not match(f, HARNESS_SKIP):
            copy(HARNESS / f, target / "harness" / f)
    for run, patterns in RUNS.items():
        base = HARNESS / "runs" / run
        for p in sorted(base.rglob("*")):
            rel = str(p.relative_to(base))
            if p.is_file() and match(rel, patterns):
                copy(p, target / "harness" / "runs" / run / rel)
    for f in tracked(V2) + ["build_submission.py"]:
        if (V2 / f).exists() and match(f, V2_TAKE) and not match(f, V2_SKIP):
            copy(V2 / f, target / DOCS / f)
    shutil.copy2(V2 / "submission_documents_README.md", target / DOCS / "README.md")
    for name, src in PACKAGE.items():
        copy(V2 / src, target / PACKAGE_DIR / name)
    for name in ROUND_PAGES:
        copy(V2 / "review" / name, target / PACKAGE_DIR / "rounds" / name)
    shutil.copy2(V2 / "submission_README.md", target / "README.md")
    shutil.copy2(HARNESS / "requirements.txt", target / "requirements.txt")
    (target / ".gitignore").write_text(
        ".DS_Store\n__pycache__/\n.venv/\n"
        "# Papers and interviews never go in this repository.\n"
        "harness/runs/*/pages/\nharness/runs/*/passages/\nharness/runs/*/segments/\nharness/runs/*/calls/\n"
        "harness/runs/*/model_coding/\nharness/runs/*/kit/\ndocuments/outputs/\n", encoding="utf-8")


def shingles(text: str) -> set[int]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {hash(" ".join(words[i:i + RUN])) for i in range(len(words) - RUN + 1)}


def check(target: Path) -> list[str]:
    problems = []
    files = [p for p in target.rglob("*") if p.is_file() and ".git" not in p.relative_to(target).parts]
    for p in files:
        rel = p.relative_to(target)
        if p.suffix.lower() == ".pdf":
            problems.append(f"{rel}: a PDF")
        if FORBIDDEN_PARTS & set(rel.parts[:-1]):
            problems.append(f"{rel}: in a folder that holds papers' text or interviews")
        if p.stat().st_size > 5_000_000:
            problems.append(f"{rel}: larger than 5 MB")
    corpus = {}  # run -> the interviews it occurs in
    for f in INTERVIEWS.glob("*.txt"):
        for h in shingles(f.read_text(encoding="utf-8", errors="ignore")):
            corpus.setdefault(h, []).append(f.name)
    for p in files:
        if p.suffix.lower() in TEXT:
            per = {}
            for h in shingles(p.read_text(encoding="utf-8", errors="ignore")):
                for name in corpus.get(h, []):
                    per[name] = per.get(name, 0) + 1
            for name, n in per.items():
                if n >= SHARED:
                    problems.append(f"{p.relative_to(target)}: {n} runs of {RUN} words also in interview {name}")
    return problems


def manifest(target: Path) -> None:
    files = sorted(p for p in target.rglob("*") if p.is_file() and ".git" not in p.relative_to(target).parts)
    (target / "MANIFEST.json").write_text(json.dumps({
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "from": {"harness": head(HARNESS), "harness_v2": head(V2)},
        "files": {str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},
        indent=1) + "\n", encoding="utf-8")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "submission" / "serendipity-harness"
    if not (target / ".git").exists():
        raise SystemExit(f"{target} is not a git repository")
    assemble(target)
    problems = check(target)
    for p in problems:
        print(p)
    if problems:
        raise SystemExit(f"{len(problems)} problems: nothing is ready to commit")
    manifest(target)
    n = sum(1 for p in target.rglob("*") if p.is_file() and ".git" not in p.relative_to(target).parts)
    print(f"{target}: {n} files, privacy check passed")


if __name__ == "__main__":
    main()
