"""The reviewed codebook.

The researchers record a decision on every draft code in a copy of the review
sheet, saved as harness/codebook/review.csv:

  decision  accept, revise or reject
  core      yes or no (for accepted and revised codes): is it one of the codes
            coders apply to every interview?
  reason    required for revise and reject

To revise a code, edit its label, definition, applies_when or
does_not_apply_when in the sheet. The harness keeps the draft wording beside
the revised wording.

Papers read after the draft are recorded in harness/codebook/added_papers.json:
their candidates add papers and passages to the draft codes they match, and their
new codes join the draft. The review sheet covers those codes too.

The frozen codebook also holds the two levels (codebook/levels.json: what coders
tick, and what is worked out after coding) and the anomaly codes, with the
fingerprints of those files and of the evidence choices (evidence_picks.json).

This stage refuses to write a codebook while any code is undecided, and never
overwrites a version that already exists.
"""
import csv
import json

from .runlog import HARNESS, Run, sha256

CODEBOOK_DIR = HARNESS / "codebook"
WORDING = ["label", "definition", "applies_when", "does_not_apply_when"]
DECISIONS = {"accept", "revise", "reject"}
EXTRA = [CODEBOOK_DIR / n for n in ("levels.json", "anomaly_codes.json", "evidence_picks.json")]


def with_added_papers(draft: dict) -> dict:
    """The draft plus the papers read after it (codebook/added_papers.json), if any."""
    path = CODEBOOK_DIR / "added_papers.json"
    if not path.exists():
        return draft
    added = json.loads(path.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in draft["codes"]}
    for m in added["maps"]:
        c, paper = by_id[m["code"]], m["candidate_id"].split(":")[0]
        c["candidate_ids"] = c["candidate_ids"] + [m["candidate_id"]]
        c["papers"] = c["papers"] + ([paper] if paper not in c["papers"] else [])
        c["passage_ids"] = c["passage_ids"] + [i for i in m["passage_ids"] if i not in c["passage_ids"]]
    for n in added["new_codes"]:
        draft["codes"].append({"id": n["id"], "group": n["group"], "label": n["label"],
                               "definition": n["definition"], "applies_when": n["applies_when"],
                               "does_not_apply_when": n["does_not_apply_when"],
                               "candidate_ids": [n["candidate_id"]],
                               "papers": [n["candidate_id"].split(":")[0]],
                               "passage_ids": n["passage_ids"], "status": "added after the draft"})
    draft["added_papers_sha256"] = sha256(path)
    return draft


def build(run: Run) -> dict:
    cfg = run.config()["codebook"]
    draft_path = HARNESS / "runs" / cfg["draft_run"] / "codebook_draft.json"
    review_path = CODEBOOK_DIR / "review.csv"
    out = CODEBOOK_DIR / f"codebook_v{cfg['version']}.json"
    if out.exists():
        raise SystemExit(f"{out.name} already exists. Set a new version in project.toml.")

    draft = with_added_papers(json.loads(draft_path.read_text(encoding="utf-8")))
    rows = {r["id"].strip(): r for r in csv.DictReader(open(review_path, encoding="utf-8-sig"))}
    problems, codes, rejected = [], [], []

    for code in draft["codes"]:
        row = rows.get(code["id"])
        if row is None:
            problems.append(f"{code['id']}: missing from the review sheet")
            continue
        decision = (row.get("decision") or "").strip().lower()
        core = (row.get("core") or "").strip().lower()
        reason = (row.get("reason") or "").strip()
        # Spreadsheet programs can alter spacing on save; that is not a revision.
        changed = [f for f in WORDING if (row.get(f) or "").split() != code[f].split()]
        if decision not in DECISIONS:
            problems.append(f"{code['id']}: decision must be one of {sorted(DECISIONS)}")
            continue
        if decision != "accept" and not reason:
            problems.append(f"{code['id']}: {decision} needs a reason")
        if decision == "accept" and changed:
            problems.append(f"{code['id']}: wording was edited ({', '.join(changed)}) "
                            "but the decision is accept; use revise")
        if decision == "revise" and not changed:
            problems.append(f"{code['id']}: decision is revise but no wording was changed")
        if decision == "reject":
            rejected.append({"id": code["id"], "label": code["label"], "reason": reason})
            continue
        if core not in ("yes", "no"):
            problems.append(f"{code['id']}: core must be yes or no")
        entry = dict(code, **{f: row[f].strip() for f in WORDING},
                     status={"accept": "accepted", "revise": "revised"}[decision], core=core == "yes", reason=reason)
        if changed:
            entry["draft_wording"] = {f: code[f] for f in changed}
        codes.append(entry)

    unknown = sorted(set(rows) - {c["id"] for c in draft["codes"]})
    problems += [f"{i}: not a code in the draft" for i in unknown]
    if problems:
        raise SystemExit("The review sheet is not complete:\n  " + "\n  ".join(problems[:40])
                         + (f"\n  and {len(problems) - 40} more" if len(problems) > 40 else ""))

    codebook = {"version": cfg["version"], "construct": draft["construct"],
                "question": draft["question"], "groups": draft["groups"],
                "built_from": {"draft": draft["version"], "draft_sha256": sha256(draft_path),
                               "added_papers_sha256": draft.get("added_papers_sha256", ""),
                               "review_sha256": sha256(review_path),
                               **{f"{f.stem}_sha256": sha256(f) for f in EXTRA if f.exists()}},
                "levels": json.loads((CODEBOOK_DIR / "levels.json").read_text(encoding="utf-8")),
                "anomaly_codes": json.loads((CODEBOOK_DIR / "anomaly_codes.json").read_text(encoding="utf-8"))["codes"],
                "codes": codes, "rejected": rejected}
    out.write_text(json.dumps(codebook, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {"version": cfg["version"], "codes": len(codes),
               "level2": len(codebook["levels"]["level2"]),
               "core": sum(c["core"] for c in codes),
               "revised": sum(c["status"] == "revised" for c in codes),
               "rejected": len(rejected), "file": out.name}
    run.log("codebook_frozen", **summary, sha256=sha256(out))
    return summary
