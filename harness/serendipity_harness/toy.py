"""Synthetic ("toy") interviews.

The real interviews cannot be published. Each one is replaced by a fictional
interview that tells a structurally equivalent story in a different setting:

  1. outline   one model reads the real interview and writes a neutral outline
  2. write     a different model writes a fictional interview from the outline
               alone; it never sees the real interview
  3. distance  fixed code checks that the fictional interview shares no names,
               figures or runs of wording with the real one

Neither model is shown the codebook.
"""
import json
import random
import re

from pydantic import BaseModel

from . import model
from .runlog import HARNESS, ROOT, Run


class Topic(BaseModel):
    topic: str
    answer_length: str  # e.g. "short (under 80 words)", "long (about 400 words)"


class Event(BaseModel):
    order: int
    stage: str
    prior_aim: str
    what_happened: str
    presented_as: str  # "planned", "unexpected" or "unclear"
    how_recognised: str
    action_taken: str
    result: str
    founder_explanation: str
    left_unclear: str
    source_segments: list[str]


class Setting(BaseModel):
    industry: str
    region: str


class Outline(BaseModel):
    is_founder_interview: bool
    reason_if_not: str
    source_setting: Setting  # the real setting, recorded only so the writer avoids it
    venture: str
    events: list[Event]
    interview_shape: list[Topic]
    voice: str
    overall_gaps: list[str]


def prompt(name: str) -> str:
    return (HARNESS / "prompts" / f"{name}.md").read_text(encoding="utf-8")


def pick_cases(run: Run) -> list[dict]:
    """A seeded random sample of the eligible interviews."""
    cfg = run.config()["toy"]
    excluded = set(run.config()["inputs"]["excluded_transcripts"])
    eligible = [c for c in run.read_json("cases.json")
                if not c["error"] and c["file"].rsplit("/", 1)[-1] not in excluded]
    return random.Random(cfg["seed"]).sample(eligible, cfg["sample_size"])


def outline(run: Run, case: dict) -> Outline | None:
    segments = [json.loads(line) for line in
                open(run.dir / "segments" / f"{case['case_id']}.jsonl", encoding="utf-8")]
    interview = "\n\n".join(f"[{s['segment_id']}]\n{s['text']}" for s in segments)
    record = model.call(run, "outline", case["case_id"], system=prompt("outline"),
                        user=interview, schema=Outline)
    if record["response"]["stop_reason"] != "end_turn":
        return None
    return Outline.model_validate_json(record["response"]["text"])


def write(run: Run, toy_id: str, outline_: Outline, target_words: int, country: str) -> str | None:
    # The writer does not receive segment identifiers: they name the real file.
    brief = outline_.model_dump(exclude={"events": {"__all__": {"source_segments"}},
                                         "is_founder_interview": True, "reason_if_not": True,
                                         "source_setting": True})
    avoid = outline_.source_setting
    user = (json.dumps(brief, ensure_ascii=False, indent=1)
            + f"\n\nSet the interview in: {country}."
            + f"\nStay away from this industry: {avoid.industry}."
            + f"\nStay away from this region: {avoid.region}."
            + f"\nTarget length: about {round(target_words, -2)} words in total.")
    record = model.call(run, "toy_writer", toy_id, system=prompt("toy_writer"), user=user)
    if record["response"]["stop_reason"] != "end_turn":
        return None
    return record["response"]["text"].strip() + "\n"


WORD = re.compile(r"[a-z0-9']+")


def distance(source: str, toy: str, run_length: int) -> dict:
    """How much of the real interview's surface survives in the fictional one."""
    header = dict(re.findall(r"^(INTERVIEW|Founder|Location|Website): (.+)$", source, re.M))
    # Whole names, not single words: company names are often made of common words.
    names = {header.get("INTERVIEW", "").strip(". "), header.get("Founder", ""),
             header.get("Location", "").split(",")[0],
             re.sub(r"^https?://(www\.)?|/.*$", "", header.get("Website", ""))}
    leaked_names = sorted(n for n in names if len(n) > 3 and n.lower() in toy.lower())

    # Dollar amounts and long numbers; years are too common to be informative.
    figure = re.compile(r"\$\s?\d[\d,.]*\s?[kKmM]?|\b\d{5,}\b")
    plain = lambda s: re.sub(r"[\s,]", "", s).lower()
    shared_figures = sorted({plain(f) for f in figure.findall(source)}
                            & {plain(f) for f in figure.findall(toy)})

    def answers(text):  # questions are generic; compare what the founder says
        return WORD.findall(" ".join(re.findall(r"^A: (.+)$", text, re.M)).lower())

    def runs(words):
        return {tuple(words[i:i + run_length]) for i in range(len(words) - run_length + 1)}

    toy_runs = runs(answers(toy))
    shared = toy_runs & runs(answers(source))
    return {"source_names_in_toy": leaked_names,
            "shared_figures": shared_figures,
            f"shared_{run_length}_word_runs": len(shared),
            "share_of_toy_runs": round(len(shared) / max(1, len(toy_runs)), 4),
            "examples": [" ".join(r) for r in sorted(shared)[:5]],
            "source_words": len(source.split()), "toy_words": len(toy.split())}


def build(run: Run) -> list[dict]:
    cfg = run.config()["toy"]
    rng = random.Random(cfg["seed"])
    rows = []
    for n, case in enumerate(pick_cases(run), 1):
        toy_id = f"toy-{n:03d}"
        source = (ROOT / case["file"]).read_text(encoding="utf-8")
        location = re.search(r"^Location: (.+)$", source, re.M)
        # Assigned by code, so settings vary and never match the real country.
        country = rng.choice([c for c in cfg["countries"]
                              if c.lower() not in (location.group(1).lower() if location else "")])
        row = {"toy_id": toy_id, "case_id": case["case_id"], "country": country, "status": "ok"}
        outline_ = outline(run, case)
        if outline_ is None:
            row["status"] = "outline call did not complete"
        elif not outline_.is_founder_interview:
            row["status"] = "not a founder interview: " + outline_.reason_if_not
        else:
            row["events"] = len(outline_.events)
            row["presented_as"] = [e.presented_as for e in outline_.events]
            row["source_setting"] = outline_.source_setting.model_dump()
            text = write(run, toy_id, outline_, case["words"], country)
            if text is None:
                row["status"] = "writer call did not complete"
            else:
                out = run.dir / "toy" / f"{toy_id}.txt"
                out.parent.mkdir(exist_ok=True)
                out.write_text(text, encoding="utf-8")
                row["distance"] = d = distance(source, text, cfg["run_length"])
                flags = [k for k in ("source_names_in_toy", "shared_figures") if d[k]]
                if d["share_of_toy_runs"] > cfg["max_shared_run_share"]:
                    flags.append("wording overlap above limit")
                row["flags"] = flags
        rows.append(row)

    # This file links fictional interviews to real ones: it stays private.
    run.write_json("private/toy_mapping.json", rows)
    calls = [json.loads(l) for l in open(run.log_path, encoding="utf-8")]
    cost = sum(c.get("cost_usd", 0) for c in calls if c["event"] == "model_call")
    run.log("toy_built", interviews=len(rows),
            written=sum(1 for r in rows if "distance" in r),
            flagged=sum(1 for r in rows if r.get("flags")), cost_usd=round(cost, 4))
    return rows
