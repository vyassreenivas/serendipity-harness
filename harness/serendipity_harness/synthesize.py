"""One draft codebook from the candidate codes of all papers.

The candidates are synthesised one group at a time. The model merges
candidates that state the same idea into a code and lists the candidates
behind each code. Fixed code then checks every candidate identifier, attaches
the papers and passages each code rests on, and lists any candidate the model
neither used nor set aside.

The result is a draft. Nothing in it is in the codebook until a researcher
has accepted it in codebook_review.csv.
"""
import csv
import json

from pydantic import BaseModel, ValidationError

from . import model
from .runlog import HARNESS, Run, sha256


class Code(BaseModel):
    label: str
    definition: str
    applies_when: str
    does_not_apply_when: str
    candidate_ids: list[str]


class SetAside(BaseModel):
    candidate_id: str
    reason: str


class Group(BaseModel):
    codes: list[Code]
    set_aside: list[SetAside]


def system_prompt(run: Run, group: dict) -> str:
    study = run.config()["study"]
    lens = f"\nRead the candidates in the light of this scope note: {study['lens']}\n" \
        if study.get("lens") else ""
    template = (HARNESS / "prompts" / "synthesize.md").read_text(encoding="utf-8")
    return (template.replace("{construct}", study["construct"])
            .replace("{question}", study["question"]).replace("{lens}", lens)
            .replace("{group}", group["name"]).replace("{asks}", group["asks"]))


def build(run: Run) -> dict:
    cfg = run.config()
    candidates = [dict(c, paper_id=record["paper_id"])
                  for path in sorted((run.dir / "candidates").glob("*.json"))
                  for record in [json.loads(path.read_text(encoding="utf-8"))]
                  for c in record["candidates"]]
    codes, set_aside, unassigned, removed, not_completed = [], [], [], [], []

    for group in cfg["codebook"]["groups"]:
        name = group["name"]
        members = [c for c in candidates if c["group"] == name]
        if not members:
            continue
        # Short identifiers within the call; mapped back to candidate identifiers below.
        short = {f"c{n:04d}": c for n, c in enumerate(members, 1)}
        lines = [f"{k} | {c['paper_id']} | {c['label']} | {c['definition']} | "
                 f"applies: {c['applies_when']} | not: {c['does_not_apply_when']}"
                 for k, c in short.items()]
        user = "\n".join(lines)
        if len(user) > cfg["extraction"]["max_chars_per_call"]:
            raise SystemExit(f"group {name}: {len(members)} candidates are too long for one "
                             "call. Raise max_chars_per_call or split the group.")
        # A large group needs a longer reply; the allowance is doubled above 300 candidates.
        call = model.call(run, "synthesize", name, system=system_prompt(run, group), user=user,
                          schema=Group, max_tokens=32000 if len(members) <= 300 else 64000)
        if call["response"]["stop_reason"] != "end_turn":
            not_completed.append(name)
            continue
        try:
            reply = Group.model_validate_json(call["response"]["text"])
        except ValidationError:  # a reply not in the required format is not used
            not_completed.append(name)
            continue

        used = set()
        for code in reply.codes:
            cited = [i.strip() for i in code.candidate_ids]
            members_of_code = [short[i] for i in cited if i in short]
            unknown = [i for i in cited if i not in short]
            if unknown:
                removed.append({"group": name, "label": code.label,
                                "candidates_not_in_group": unknown,
                                "code_dropped": not members_of_code})
            if not members_of_code:  # a code no candidate supports has no source
                continue
            used.update(i for i in cited if i in short)
            n = sum(1 for c in codes if c["group"] == name) + 1
            codes.append({
                "id": f"{name}-{n:02d}", "group": name, "label": code.label,
                "definition": code.definition, "applies_when": code.applies_when,
                "does_not_apply_when": code.does_not_apply_when,
                "candidate_ids": [c["candidate_id"] for c in members_of_code],
                "papers": sorted({c["paper_id"] for c in members_of_code}),
                "passage_ids": sorted({p for c in members_of_code for p in c["passage_ids"]}),
                "status": "draft"})
        for item in reply.set_aside:
            if item.candidate_id.strip() in short:
                used.add(item.candidate_id.strip())
                set_aside.append({"candidate_id": short[item.candidate_id.strip()]["candidate_id"],
                                  "group": name, "reason": item.reason})
        unassigned += [c["candidate_id"] for k, c in short.items() if k not in used]

    draft = {"version": f"draft-{run.dir.name}", "construct": cfg["study"]["construct"],
             "question": cfg["study"]["question"], "groups": cfg["codebook"]["groups"],
             "codes": codes, "set_aside": set_aside, "unassigned_candidates": unassigned,
             "removed": removed}
    run.write_json("codebook_draft.json", draft)

    # The sheet on which the researchers record what enters the codebook.
    with open(run.dir / "codebook_review.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "group", "label", "definition", "applies_when",
                         "does_not_apply_when", "papers", "paper_ids",
                         "decision", "core", "reason"])
        for c in codes:
            writer.writerow([c["id"], c["group"], c["label"], c["definition"], c["applies_when"],
                             c["does_not_apply_when"], len(c["papers"]), "; ".join(c["papers"]),
                             "", "", ""])

    summary = {"candidates": len(candidates), "codes": len(codes), "set_aside": len(set_aside),
               "unassigned_candidates": len(unassigned),
               "codes_dropped": sum(r["code_dropped"] for r in removed),
               "groups_not_completed": not_completed}
    run.log("codebook_synthesised", **summary,
            prompt_sha256=sha256(HARNESS / "prompts" / "synthesize.md"))
    return summary
