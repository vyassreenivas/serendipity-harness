"""Set up a coding round: draw its interviews, cut them into segments, write a coder prompt for each.

Usage: python -m serendipity_harness.rounds WORK_DIR --codebook PATH --draw N --seed SEED
           [--recode EARLIER_WORK_DIR ...] [--exclude-manifest FILE ...]

A round codes N interviews not coded before, drawn by a recorded seed from the
corpus ([coding] corpus_dir in project.toml), and recodes every interview of
the earlier rounds named with --recode, so all are coded with the same codebook
version. Interviews in an earlier round or in a manifest given with
--exclude-manifest (for example the pilot) are never drawn.

Writes, in WORK_DIR:
  cases.json                      the round's interviews: new ones first, then recoded ones
  checked/<case>.segments.json    each interview's numbered segments
  prompts/<case>.md               the coder prompt: the codebook, the task, the interview, the reply format
  round.json                      the codebook (path, version, fingerprint), seed, corpus and exclusions
and in WORK_DIR/interviews/ a copy of each interview with MANIFEST.txt, for the
researchers. Both hold interview text: keep WORK_DIR out of git.

Each prompt is answered as replies/<case>.json, by a model call or in a session,
and coded_pages then checks the replies and writes the pages.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import tomllib
from datetime import date
from pathlib import Path

from .model_coding import InterviewCoding, codebook_from, numbered, system_prompt, task
from .runlog import HARNESS, ROOT, sha256
from .transcripts import segment


def case_id(path: Path) -> str:
    return f"{path.stem[:40].rstrip('-')}-{sha256(path)[:6]}"


def prompt(cb: dict, segments: list[dict]) -> str:
    return ("# SYSTEM PROMPT\n\n" + system_prompt(cb) + "\n\n# USER MESSAGE\n\n" + task("interview", cb)
            + "\n\nThe interview:\n\n" + numbered(segments) + "\n\n# REPLY FORMAT\n\n"
            + "Reply with one JSON object that matches this JSON schema exactly (no other text):\n\n"
            + json.dumps(InterviewCoding.model_json_schema(), indent=1) + "\n")


def build(work: Path, codebook: Path, draw: int, seed: int, recode: list[Path], exclude: list[Path]) -> dict:
    cfg = tomllib.loads((HARNESS / "project.toml").read_text(encoding="utf-8"))
    corpus = ROOT / cfg["coding"]["corpus_dir"]
    cb = codebook_from(json.loads(codebook.read_text(encoding="utf-8")))
    earlier = [c for w in recode for c in json.loads((w / "cases.json").read_text(encoding="utf-8"))]
    taken = {c["file"] for c in earlier}
    for m in exclude:
        taken |= {line.split()[0] if line.split()[0].endswith(".txt") else line.split()[1]
                  for line in m.read_text(encoding="utf-8").splitlines()
                  if ".txt" in line and line.split()}
    pool = [n for n in sorted(p.name for p in corpus.glob("*.txt")) if n not in taken]
    new = random.Random(seed).sample(pool, draw)
    files = [(n, "new") for n in new] + [(c["file"], "recode") for c in earlier]

    for sub in ("checked", "prompts", "interviews"):
        (work / sub).mkdir(parents=True, exist_ok=True)
    cases, manifest = [], [f"{len(files)} Starter Story interviews for a coding round, {date.today().isoformat()}: "
                           f"{draw} drawn with random.Random({seed}).sample(sorted file names not coded before, {draw}), "
                           f"then {len(earlier)} recoded from earlier rounds.",
                           f"Source: {corpus.relative_to(ROOT)}. Proprietary text: for the researchers only; do not share or submit.", ""]
    for k, (name, how) in enumerate(files, 1):
        path = corpus / name
        cid = case_id(path)
        segs = segment(path.read_text(encoding="utf-8"))
        for i, s in enumerate(segs, 1):
            s["segment_id"] = f"{cid}:s{i:02d}"
        (work / "checked" / f"{cid}.segments.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1) + "\n",
                                                               encoding="utf-8")
        (work / "prompts" / f"{cid}.md").write_text(prompt(cb, segs), encoding="utf-8")
        shutil.copy2(path, work / "interviews" / name)
        cases.append({"case_no": f"{k:02d}", "case_id": cid, "file": name, "segments": len(segs),
                      "words": len(path.read_text(encoding="utf-8").split()), "in_round": how})
        manifest.append(f"{k:02d}  {name}  {how}  sha256 {sha256(path)[:12]}")
    (work / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (work / "interviews" / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    info = {"made": date.today().isoformat(), "codebook": str(codebook.resolve().relative_to(ROOT)),
            "codebook_version": cb["version"], "codebook_sha256": sha256(codebook), "seed": seed, "drawn": draw,
            "corpus": str(corpus.relative_to(ROOT)), "corpus_files": len(list(corpus.glob("*.txt"))),
            "recoded_from": [str(w.resolve().relative_to(ROOT)) for w in recode],
            "excluded_manifests": [str(m.resolve().relative_to(ROOT)) for m in exclude],
            "excluded_files": len(taken), "coder_prompt_sha256": sha256(HARNESS / "prompts" / "coder.md")}
    (work / "round.json").write_text(json.dumps(info, indent=1) + "\n", encoding="utf-8")
    return info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("work", type=Path)
    ap.add_argument("--codebook", type=Path, required=True)
    ap.add_argument("--draw", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--recode", type=Path, nargs="*", default=[])
    ap.add_argument("--exclude-manifest", type=Path, nargs="*", default=[])
    a = ap.parse_args()
    print(json.dumps(build(a.work, a.codebook, a.draw, a.seed, a.recode, a.exclude_manifest), indent=1))


if __name__ == "__main__":
    main()
