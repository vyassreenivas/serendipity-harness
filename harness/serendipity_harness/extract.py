"""Candidate codes from each paper.

The model reads one paper as numbered passages and proposes candidate codes.
For every candidate it names the passages that state the idea. Fixed code
then checks each passage identifier against the saved passages and removes
any that do not exist, so a candidate is always tied to real pages of the
paper. The model never types a quotation.

Papers listed as methods papers in the run setup are not read.
"""
from typing import Literal
import json

from pydantic import ValidationError, create_model

from . import model
from .runlog import HARNESS, ROOT, Run, sha256


def schema(groups: list[str]):
    """The reply format. The group has to be one of the groups in the run setup."""
    candidate = create_model(
        "Candidate", group=(Literal[tuple(groups)], ...), label=(str, ...),
        definition=(str, ...), applies_when=(str, ...), does_not_apply_when=(str, ...),
        passage_ids=(list[str], ...))
    return create_model(
        "Extraction", about=(str, ...), bearing=(Literal["central", "partial", "none"], ...),
        candidates=(list[candidate], ...))


def system_prompt(run: Run) -> str:
    cfg = run.config()
    groups = "\n".join(f"- {g['name']}: {g['asks']}" for g in cfg["codebook"]["groups"])
    template = (HARNESS / "prompts" / "extract.md").read_text(encoding="utf-8")
    return (template.replace("{construct}", cfg["study"]["construct"])
            .replace("{question}", cfg["study"]["question"]).replace("{groups}", groups))


def papers_to_read(run: Run, only_new: bool = False) -> list[dict]:
    """Papers to read for candidate codes. With only_new, just the papers the draft named in
    project.toml (codebook.draft_run) has not read yet, so the draft itself is left as it is."""
    cfg = run.config()
    listed = (ROOT / cfg["inputs"]["methods_papers"]).read_text(encoding="utf-8").splitlines()
    methods = {line.strip() for line in listed if line.strip() and not line.startswith("#")}
    papers = [p for p in run.read_json("inventory.json")
              if not p["duplicate_of"] and not p["error"]
              and p["file"].rsplit("/", 1)[-1] not in methods]
    if only_new:
        read = {f.stem for f in (HARNESS / "runs" / cfg["codebook"]["draft_run"] / "candidates").glob("*.json")}
        newer = set(cfg["extraction"].get("newer_versions_of_read_papers", []))
        return [p for p in papers if p["paper_id"] not in read and p["file"].rsplit("/", 1)[-1] not in newer]
    return papers[:cfg["extraction"]["paper_sample"] or None]


def parts(passages: list[dict], max_chars: int) -> list[list[dict]]:
    """Consecutive runs of passages, each small enough for one call."""
    out, size = [[]], 0
    for p in passages:
        if out[-1] and size + len(p["text"]) > max_chars:
            out.append([])
            size = 0
        out[-1].append(p)
        size += len(p["text"])
    return out


def build(run: Run, only_new: bool = False) -> dict:
    cfg = run.config()
    reply_format = schema([g["name"] for g in cfg["codebook"]["groups"]])
    system = system_prompt(run)
    summary = {"papers": 0, "candidates": 0, "candidates_removed": 0, "not_completed": []}

    for paper in papers_to_read(run, only_new):
        pid = paper["paper_id"]
        passages = [json.loads(line) for line in
                    open(run.dir / "passages" / f"{pid}.jsonl", encoding="utf-8")]
        by_short_id = {p["passage_id"].split(":", 1)[1]: p for p in passages}
        chunks = parts(passages, cfg["extraction"]["max_chars_per_call"])
        record = {"paper_id": pid, "file": paper["file"], "about": [], "bearing": [],
                  "candidates": [], "removed": []}

        for n, chunk in enumerate(chunks, 1):
            note = f"Part {n} of {len(chunks)} of this paper.\n\n" if len(chunks) > 1 else ""
            text = "\n\n".join(f"[{p['passage_id'].split(':', 1)[1]}] {p['text']}" for p in chunk)
            key = pid if len(chunks) == 1 else f"{pid}-part{n}"
            call = model.call(run, "extract", key, system=system, user=note + text,
                              schema=reply_format, cache_system=True)
            if call["response"]["stop_reason"] != "end_turn":
                summary["not_completed"].append(key)
                continue
            try:
                reply = reply_format.model_validate_json(call["response"]["text"])
            except ValidationError:  # a reply not in the required format is not used
                summary["not_completed"].append(key)
                continue
            add_reply(record, reply, by_short_id)
        finish(run, record, summary)

    run.log("candidates_extracted", **summary,
            prompt_sha256=sha256(HARNESS / "prompts" / "extract.md"))
    return summary


def add_reply(record: dict, reply, by_short_id: dict) -> None:
    """Check each cited passage against the saved passages; drop candidates with none."""
    record["about"].append(reply.about)
    record["bearing"].append(reply.bearing)
    for c in reply.candidates:
        cited = [i.strip("[] ") for i in c.passage_ids]
        found = [by_short_id[i] for i in cited if i in by_short_id]
        missing = [i for i in cited if i not in by_short_id]
        entry = {"group": c.group, "label": c.label, "definition": c.definition,
                 "applies_when": c.applies_when,
                 "does_not_apply_when": c.does_not_apply_when,
                 "passage_ids": [p["passage_id"] for p in found],
                 "pdf_pages": sorted({p["pdf_page"] for p in found})}
        if missing:
            record["removed"].append({"label": c.label, "passages_not_in_paper": missing,
                                      "candidate_dropped": not found})
        if found:  # a candidate with no real passage has no evidence and is dropped
            record["candidates"].append(entry)


def finish(run: Run, record: dict, summary: dict) -> None:
    pid = record["paper_id"]
    for n, entry in enumerate(record["candidates"], 1):
        entry["candidate_id"] = f"{pid}:c{n:02d}"
    run.write_json(f"candidates/{pid}.json", record)
    summary["papers"] += 1
    summary["candidates"] += len(record["candidates"])
    summary["candidates_removed"] += sum(r["candidate_dropped"] for r in record["removed"])


def from_inapp(run: Run, read_by: str) -> dict:
    """Candidates from replies written in an interactive session (inapp/<paper_id>.json)
    instead of an API call. The reader saw the same prompt (inapp/system_prompt.md) and the
    same passages; the replies pass the same format and passage checks as build(). Each
    record says who read the paper, so these are never mistaken for API output."""
    reply_format = schema([g["name"] for g in run.config()["codebook"]["groups"]])
    inventory = {p["paper_id"]: p for p in run.read_json("inventory.json")}
    summary = {"papers": 0, "candidates": 0, "candidates_removed": 0, "not_completed": []}
    for path in sorted((run.dir / "inapp").glob("*.json")):
        pid = path.stem
        passages = [json.loads(line) for line in
                    open(run.dir / "passages" / f"{pid}.jsonl", encoding="utf-8")]
        by_short_id = {p["passage_id"].split(":", 1)[1]: p for p in passages}
        try:
            reply = reply_format.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError:
            summary["not_completed"].append(pid)
            continue
        record = {"paper_id": pid, "file": inventory[pid]["file"], "read_by": read_by,
                  "reply_sha256": sha256(path), "about": [], "bearing": [],
                  "candidates": [], "removed": []}
        add_reply(record, reply, by_short_id)
        finish(run, record, summary)
    run.log("candidates_extracted_inapp", read_by=read_by, **summary,
            prompt_sha256=sha256(run.dir / "inapp" / "system_prompt.md"))
    return summary
