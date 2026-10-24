"""Model coding of interviews.

The model receives the same instructions and the same core codes as the
human coders and fills in the same worksheet. Fixed code then checks every
entry: a code that is not a core code on that axis, or a paragraph number that
does not exist, is removed and recorded.

Two procedures give the same worksheet. In the single procedure the model
codes an interview in one reply. In the staged procedure (staged = true in the
run setup) the work is cut into small steps, each a separate call: find the
episodes; judge each episode against the two definitions; apply the codes one
group at a time; say whether anything was left uncaptured. In every staged
reply the reasoning comes before the answer.

The model's worksheet is written inside the run folder. It is copied into
harness/coding/ for comparison only after the human coders have finished.
"""
from typing import Literal
import csv
import json

from pydantic import BaseModel, ValidationError

from . import coding, model
from .runlog import HARNESS, Run

Verdict = Literal["supported", "not supported", "unresolved"]
Expectation = Literal["stated", "label only", "not stated"]


class Episode(BaseModel):
    paragraphs: list[int]
    what_was_unexpected: str
    prior_expectation: Expectation
    narrow: Verdict
    narrow_rationale: str
    broad: Verdict
    broad_rationale: str
    DEF: list[str]
    TYP: list[str]
    TRG: list[str]
    MEC: list[str]
    LOC: list[str]
    ROL: list[str]
    OUT: list[str]
    ACC: list[str]
    RIV: list[str]
    BND: list[str]
    no_rival_plausible: bool
    candidate_code: str
    almost_fit: str
    notes: str


class Coding(BaseModel):
    episodes: list[Episode]
    interview_notes: str


def system_prompt(run: Run) -> str:
    lines, axis = [], None
    for c in coding.core_codes(run):
        if c["id"] in coding.VERDICT_CODES:
            continue  # the two definitions are applied as verdicts, not as codes
        if c["axis"] != axis:
            axis = c["axis"]
            lines.append(f"\nAxis: {c['axis_name']} (codes starting {axis})")
        lines.append(f"- {c['id']} | {c['label']} | {c['meaning']} | {c['evidence_and_distinction']}")
    template = (HARNESS / "prompts" / "coder.md").read_text(encoding="utf-8")
    return template.replace("{codes}", "\n".join(lines).strip())


def to_rows(case_no: str, case_id: str, result: Coding, n_segments: int,
            known_codes: dict[str, str]) -> tuple[list[dict], list[str]]:
    """Turn the model's reply into worksheet rows, removing invalid entries."""
    base = {"case_no": case_no, "case_id": case_id}
    if not result.episodes:
        return [{**base, "episode": 0, "notes": result.interview_notes}], []
    rows, removed = [], []
    for k, ep in enumerate(result.episodes, 1):
        paragraphs = sorted({p for p in ep.paragraphs if 1 <= p <= n_segments})
        removed += [f"{case_id} episode {k}: paragraph {p} does not exist"
                    for p in ep.paragraphs if not 1 <= p <= n_segments]
        row = {**base, "episode": k, "segments": ", ".join(map(str, paragraphs)),
               "what_was_unexpected": ep.what_was_unexpected,
               "prior_expectation": ep.prior_expectation,
               "narrow": ep.narrow, "broad": ep.broad,
               "candidate_code": ep.candidate_code, "almost_fit": ep.almost_fit,
               "notes": f"narrow: {ep.narrow_rationale} | broad: {ep.broad_rationale} | {ep.notes}"}
        for axis, name in coding.AXIS_NAMES.items():
            valid = [c for c in getattr(ep, axis)
                     if known_codes.get(c) == axis and c not in coding.VERDICT_CODES]
            removed += [f"{case_id} episode {k}: {c} is not a core {name} code"
                        for c in getattr(ep, axis) if c not in valid]
            row[name] = " ".join(valid)
        if ep.no_rival_plausible and not row["rival"]:
            row["rival"] = "none"
        rows.append(row)
    return rows, removed


# ---- staged procedure ----

class FoundEpisode(BaseModel):
    paragraphs: list[int]
    what_was_unexpected: str


class Episodes(BaseModel):
    considered: str
    episodes: list[FoundEpisode]


class Verdicts(BaseModel):
    expectation_evidence: str
    prior_expectation: Expectation
    narrow_reasoning: str
    narrow: Verdict
    broad_reasoning: str
    broad: Verdict


class GroupCodes(BaseModel):
    reasoning: str
    codes: list[str]


class Candidate(BaseModel):
    reasoning: str
    candidate_code: str
    almost_fit: str


RIVAL_NOTE = ("- A rival explanation does not cancel serendipity; both can hold. List every rival "
              "the paragraphs also give evidence for.\n")


def ask(run: Run, key: str, prompt: str, user: str, schema, failed: list):
    """One staged call. A reply that is cut off or in the wrong form is recorded, not used."""
    record = model.call(run, "coder", key, system=prompt, user=user, schema=schema,
                        max_tokens=4000)
    if record["response"]["stop_reason"] == "end_turn":
        try:
            return schema.model_validate_json(record["response"]["text"])
        except ValidationError:
            pass
    failed.append(key)
    return None


def staged_rows(run: Run, case_no: str, case_id: str, segments: list[dict], codes: list[dict],
                removed: list, failed: list) -> list[dict]:
    prompts = {f.stem: f.read_text(encoding="utf-8")
               for f in (HARNESS / "prompts" / "coder_staged").glob("*.md")}
    asks = {g["name"]: g["asks"] for g in run.config()["codebook"]["groups"]}
    base = {"case_no": case_no, "case_id": case_id}
    numbered = [f"[{k}] {s['text']}" for k, s in enumerate(segments, 1)]
    interview = "\n\n".join(numbered)

    found = ask(run, f"{case_id}-1", prompts["1_episodes"], interview, Episodes, failed)
    if found is None:
        return []
    episodes = []
    for ep in found.episodes:
        paragraphs = sorted({p for p in ep.paragraphs if 1 <= p <= len(segments)})
        removed += [f"{case_id}: paragraph {p} does not exist"
                    for p in ep.paragraphs if not 1 <= p <= len(segments)]
        if paragraphs:  # an episode with no real paragraph has no evidence
            episodes.append((paragraphs, ep.what_was_unexpected))
    if not episodes:
        return [{**base, "episode": 0, "notes": found.considered}]

    labels = "\n".join(f"{c['axis_name']}: {c['id']} {c['label']}" for c in codes
                       if c["id"] not in coding.VERDICT_CODES)
    rows = []
    for k, (paragraphs, unexpected) in enumerate(episodes, 1):
        head = f"Episode: {unexpected}\nParagraphs: {', '.join(map(str, paragraphs))}"
        excerpt = head + "\n\n" + "\n\n".join(numbered[p - 1] for p in paragraphs)
        row = {**base, "episode": k, "segments": ", ".join(map(str, paragraphs)),
               "what_was_unexpected": unexpected}

        verdict = ask(run, f"{case_id}-e{k}-2", prompts["2_verdicts"],
                      head + "\n\nThe interview:\n\n" + interview, Verdicts, failed)
        if verdict:
            row.update(prior_expectation=verdict.prior_expectation, narrow=verdict.narrow,
                       broad=verdict.broad,
                       notes=f"narrow: {verdict.narrow_reasoning} | broad: {verdict.broad_reasoning}")

        applied = []
        for axis, name in coding.AXIS_NAMES.items():
            group = [c for c in codes if c["axis"] == axis and c["id"] not in coding.VERDICT_CODES]
            listing = "\n".join(f"- {c['id']} | {c['label']} | {c['meaning']} | "
                                f"{c['evidence_and_distinction']}" for c in group)
            prompt = (prompts["3_codes"].replace("{group}", name).replace("{asks}", asks[name])
                      .replace("{codes}", listing)
                      .replace("{extra}", RIVAL_NOTE if axis == "RIV" else ""))
            reply = ask(run, f"{case_id}-e{k}-3-{name}", prompt, excerpt, GroupCodes, failed)
            if reply is None:
                continue
            ids = {c["id"] for c in group}
            valid = [c for c in dict.fromkeys(reply.codes) if c in ids]
            removed += [f"{case_id} episode {k}: {c} is not a core {name} code"
                        for c in reply.codes if c not in ids]
            # The rival call exists to weigh rivals, so an empty answer means none was found.
            row[name] = " ".join(valid) or ("none" if axis == "RIV" else "")
            applied += valid

        candidate = ask(run, f"{case_id}-e{k}-4", prompts["4_candidate"].replace("{labels}", labels),
                        excerpt + "\n\nCodes already applied: " + (" ".join(applied) or "none"),
                        Candidate, failed)
        if candidate:
            row.update(candidate_code=candidate.candidate_code, almost_fit=candidate.almost_fit)
        rows.append(row)
    return rows


def build(run: Run) -> dict:
    cfg = run.config()["coding"]
    cases = coding.eligible_cases(run)
    if cfg["model_sample"]:
        cases = cases[:cfg["model_sample"]]  # the first interviews in worksheet order
    codes = coding.core_codes(run)
    known_codes = {c["id"]: c["axis"] for c in codes}
    system = system_prompt(run)

    rows, removed, failed = [], [], []
    for n, case in enumerate(cases, 1):
        segments = [json.loads(line) for line in
                    open(run.dir / "segments" / f"{case['case_id']}.jsonl", encoding="utf-8")]
        if cfg.get("staged"):
            rows += staged_rows(run, f"{n:03d}", case["case_id"], segments, codes, removed, failed)
            continue
        interview = "\n\n".join(f"[{k}] {s['text']}" for k, s in enumerate(segments, 1))
        record = model.call(run, "coder", case["case_id"], system=system, user=interview,
                            schema=Coding, cache_system=True)
        if record["response"]["stop_reason"] != "end_turn":
            failed.append(case["case_id"])
            continue
        try:
            result = Coding.model_validate_json(record["response"]["text"])
        except ValidationError:  # a reply that is not in the worksheet format is not coded
            failed.append(case["case_id"])
            continue
        new_rows, new_removed = to_rows(f"{n:03d}", case["case_id"], result,
                                        len(segments), known_codes)
        rows += new_rows
        removed += new_removed

    name = run.config()["models"]["coder"]["model"]
    out = run.dir / "model_coding" / f"{name}.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=coding.FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    run.write_json("model_coding/removed_entries.json", removed)

    log = [json.loads(l) for l in open(run.log_path, encoding="utf-8")]
    cost = sum(e.get("cost_usd", 0) for e in log if e["event"] == "model_call")
    summary = {"interviews": len(cases), "not_completed": failed,
               "episodes": sum(1 for r in rows if r["episode"]),
               "interviews_without_episode": sum(1 for r in rows if not r["episode"]),
               "entries_removed": len(removed), "cost_usd": round(cost, 4)}
    run.log("model_coding_built", model=name, staged=bool(cfg.get("staged")), **summary)
    return summary
