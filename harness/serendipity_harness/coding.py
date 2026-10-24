"""Coding worksheets and agreement between coders.

Human coders and the model fill in the same worksheet: one row per episode.
An episode is a stretch of the founder's account about one unexpected event
and what came of it. An interview with no such stretch gets a single row with
episode 0.

  kit      writes the reading copies, the list of core codes and a blank
           worksheet for each coder
  compare  reads the completed worksheets in harness/coding/ and reports
           agreement for every pair of coders, the candidate codes coders
           proposed, and how often each core code was used

Code IDs keep their three-letter prefix (MEC2) so they match the 163-code
reference codebook. Worksheet column headers use the plain word for each
prefix (AXIS_NAMES).
"""
from itertools import combinations
import csv
import json
import random
import re
import shutil

from .runlog import HARNESS, ROOT, Run, sha256

AXIS_NAMES = {"DEF": "definition", "TYP": "type", "TRG": "trigger", "MEC": "mechanism",
              "LOC": "background", "ROL": "role", "OUT": "outcome", "ACC": "account",
              "RIV": "rival", "BND": "condition"}
AXES = list(AXIS_NAMES)
VERDICT_CODES = {"DEF1", "DEF7"}  # applied as the narrow and broad verdicts, not entered as codes
VERDICTS = {"supported", "not supported", "unresolved"}
EXPECTATION = {"stated", "label only", "not stated"}
FIELDS = (["case_no", "case_id", "episode", "segments", "what_was_unexpected",
           "prior_expectation", "narrow", "broad"]
          + list(AXIS_NAMES.values()) + ["candidate_code", "almost_fit", "notes"])
CODING_DIR = HARNESS / "coding"
CODEBOOK_DIR = HARNESS / "codebook"


def quote_checks() -> dict[str, dict]:
    """The most recent quotation check, by code: PDF page and how closely the words match."""
    runs = sorted((HARNESS / "runs").glob("*/quote_check.csv"))
    if not runs:
        return {}
    return {r["code_id"]: r for r in csv.DictReader(open(runs[-1], encoding="utf-8"))}


def core_codes(run: Run) -> list[dict]:
    """The codes coders apply: the reference codebook's core tier, in the kit's wording."""
    codebook = json.loads((ROOT / run.config()["inputs"]["codebook"]).read_text(encoding="utf-8"))
    kit_wording = json.loads((CODEBOOK_DIR / "kit_wording.json").read_text(encoding="utf-8"))
    checks = quote_checks()
    codes = []
    for c in codebook["codes"]:
        v3, check = c["original_v3"], checks.get(c["id"], {})
        if v3["tier"] != "A" or c["id"] in kit_wording["memo_only"]:
            continue
        codes.append({
            "id": c["id"], "axis": c["axis"], "axis_name": AXIS_NAMES[c["axis"]],
            "label": c["editorial"]["label"], "meaning": c["editorial"]["meaning"],
            "evidence_and_distinction": kit_wording["evidence_and_distinction"].get(
                c["id"], c["editorial"]["evidence_and_distinction"]),
            "source_paper": v3["quote_source"], "source_pdf_page": check.get("pdf_pages", ""),
            "source_quote": v3["quote"], "quote_match": check.get("level", "not checked"),
            "also_backed_by": "; ".join(v3["backing"]),
            "example_from_interviews": "",
            "status": "core", "version": kit_wording["version"]})
    return codes


def eligible_cases(run: Run) -> list[dict]:
    """Eligible interviews in a seeded random order, the same for every coder."""
    cfg = run.config()
    excluded = set(cfg["inputs"]["excluded_transcripts"])
    cases = [c for c in run.read_json("cases.json")
             if not c["error"] and c["file"].rsplit("/", 1)[-1] not in excluded]
    random.Random(cfg["coding"]["order_seed"]).shuffle(cases)
    return cases


def kit(run: Run) -> dict:
    cfg = run.config()["coding"]
    kit_dir = run.dir / "kit"
    (kit_dir / "reading").mkdir(parents=True)
    cases = eligible_cases(run)

    for n, case in enumerate(cases, 1):
        segments = [json.loads(line) for line in
                    open(run.dir / "segments" / f"{case['case_id']}.jsonl", encoding="utf-8")]
        body = "\n\n".join(f"[{k}] {s['text']}" for k, s in enumerate(segments, 1))
        (kit_dir / "reading" / f"{n:03d}_{case['case_id']}.txt").write_text(
            f"Case {n:03d}   {case['case_id']}\n\n{body}\n", encoding="utf-8")

    codes = core_codes(run)
    with open(kit_dir / "core_codes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(codes[0]))
        writer.writeheader()
        writer.writerows(codes)
    shutil.copy(CODEBOOK_DIR / "changes.csv", kit_dir / "codebook_changes.csv")

    for coder in cfg["coders"]:
        with open(kit_dir / f"worksheet_{coder}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            for n, case in enumerate(cases, 1):
                writer.writerow({"case_no": f"{n:03d}", "case_id": case["case_id"]})

    run.log("coding_kit_built", cases=len(cases), core_codes=len(codes), coders=cfg["coders"],
            order_seed=cfg["order_seed"], codebook_version=codes[0]["version"],
            kit_wording_sha256=sha256(CODEBOOK_DIR / "kit_wording.json"))
    return {"cases": len(cases), "core_codes": len(codes), "kit": str(kit_dir.relative_to(ROOT))}


# ---- reading completed worksheets ----

def parse_segments(text: str) -> set[int]:
    """'7-9, 12' -> {7, 8, 9, 12}"""
    out = set()
    for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", text or ""):
        out.update(range(int(a), int(b or a) + 1))
    return out


def load(path, known_cases: set[str], known_codes: dict[str, str]) -> tuple[dict, list[str]]:
    """Return {case_id: [episode, ...]} and a list of problems found in the file."""
    cases, problems = {}, []
    for line_no, row in enumerate(csv.DictReader(open(path, encoding="utf-8-sig")), 2):
        case_id = (row.get("case_id") or "").strip()
        episode = (row.get("episode") or "").strip()
        if not case_id or episode == "":
            continue  # not coded yet
        if case_id not in known_cases:
            problems.append(f"line {line_no}: unknown case_id {case_id}")
            continue
        episodes = cases.setdefault(case_id, [])
        if episode == "0":
            continue  # coded, no episode found
        entry = {"case_id": case_id, "segments": parse_segments(row.get("segments")), "codes": {},
                 "candidate_code": (row.get("candidate_code") or "").strip(),
                 "almost_fit": (row.get("almost_fit") or "").strip()}
        if not entry["segments"]:
            problems.append(f"line {line_no}: episode has no segment numbers")
        entry["prior_expectation"] = (row.get("prior_expectation") or "").strip().lower()
        if entry["prior_expectation"] not in EXPECTATION:
            problems.append(f"line {line_no}: prior_expectation must be one of {sorted(EXPECTATION)}")
        for template in ("narrow", "broad"):
            entry[template] = (row.get(template) or "").strip().lower()
            if entry[template] not in VERDICTS:
                problems.append(f"line {line_no}: {template} must be one of {sorted(VERDICTS)}")
        for axis, name in AXIS_NAMES.items():
            ids = set(re.findall(r"[A-Z]{3}\d+", (row.get(name) or "").upper()))
            for code in sorted(ids):
                if code in VERDICT_CODES:
                    problems.append(f"line {line_no}: {code} is a verdict column, not a {name} code")
                elif known_codes.get(code) != axis:
                    problems.append(f"line {line_no}: {code} is not a core {name} code")
            entry["codes"][axis] = ids - VERDICT_CODES
        # A supported verdict has to show which other explanation was weighed.
        rival = (row.get("rival") or "").strip().lower()
        if "supported" in (entry["narrow"], entry["broad"]) and not entry["codes"]["RIV"] \
                and rival != "none":
            problems.append(f"line {line_no}: a supported episode needs a rival code, or 'none'")
        episodes.append(entry)
    return cases, problems


# ---- agreement ----

def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa: agreement beyond what the two coders' base rates would give."""
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    labels = {x for pair in pairs for x in pair}
    expected = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n)
                   for l in labels)
    return None if expected == 1 else round((observed - expected) / (1 - expected), 3)


def case_verdict(episodes: list[dict], template: str) -> str:
    verdicts = {e[template] for e in episodes}
    if "supported" in verdicts:
        return "supported"
    return "unresolved" if "unresolved" in verdicts else "not supported"


def match_episodes(a: list[dict], b: list[dict]) -> list[tuple[dict, dict]]:
    """Pair episodes that share the most segments; each episode is used once."""
    candidates = sorted(((len(x["segments"] & y["segments"]), i, j)
                         for i, x in enumerate(a) for j, y in enumerate(b)
                         if x["segments"] & y["segments"]), reverse=True)
    used_a, used_b, pairs = set(), set(), []
    for _, i, j in candidates:
        if i not in used_a and j not in used_b:
            used_a.add(i), used_b.add(j), pairs.append((a[i], b[j]))
    return pairs


def agreement(a: dict, b: dict) -> dict:
    shared = sorted(set(a) & set(b))
    result = {"cases_coded_by_both": len(shared)}
    for template in ("narrow", "broad"):
        pairs = [(case_verdict(a[c], template), case_verdict(b[c], template)) for c in shared]
        result[f"case_verdict_{template}"] = {
            "agree": sum(x == y for x, y in pairs), "of": len(pairs), "kappa": kappa(pairs)}

    matched = [pair for c in shared for pair in match_episodes(a[c], b[c])]
    result["episodes"] = {"coder_a": sum(len(a[c]) for c in shared),
                          "coder_b": sum(len(b[c]) for c in shared),
                          "matched": len(matched)}
    for template in ("narrow", "broad"):
        pairs = [(x[template], y[template]) for x, y in matched]
        result[f"episode_verdict_{template}"] = {
            "agree": sum(p == q for p, q in pairs), "of": len(pairs), "kappa": kappa(pairs)}

    # Codes are compared on matched episodes: shared codes / codes either coder applied.
    result["codes_by_axis"] = {}
    for axis in AXES:
        both = sum(len(x["codes"][axis] & y["codes"][axis]) for x, y in matched)
        either = sum(len(x["codes"][axis] | y["codes"][axis]) for x, y in matched)
        result["codes_by_axis"][axis] = {"both": both, "either": either,
                                         "overlap": round(both / either, 3) if either else None}
    return result


def candidates(coders: dict) -> list[dict]:
    """Every candidate code a coder proposed, for review between rounds."""
    return [{"coder": name, "case_id": e["case_id"], "segments": sorted(e["segments"]),
             "candidate_code": e["candidate_code"], "almost_fit": e["almost_fit"]}
            for name, cases in coders.items() for episodes in cases.values()
            for e in episodes if e["candidate_code"]]


def code_use(coders: dict, known_codes: dict[str, str]) -> dict:
    """Episodes each core code was applied to, per coder. Unused codes are listed
    so the review can ask whether they should be kept, merged or dropped."""
    use = {code: {name: 0 for name in coders} for code in known_codes
           if code not in VERDICT_CODES}
    for name, cases in coders.items():
        for episodes in cases.values():
            for e in episodes:
                for ids in e["codes"].values():
                    for code in ids & set(use):
                        use[code][name] += 1
    return {"by_code": use,
            "used_by_no_coder": sorted(c for c, n in use.items() if not any(n.values()))}


def compare(run: Run) -> dict:
    known_cases = {c["case_id"] for c in eligible_cases(run)}
    known_codes = {c["id"]: c["axis"] for c in core_codes(run)}
    coders, problems = {}, {}
    for path in sorted(CODING_DIR.glob("*.csv")):
        coders[path.stem], problems[path.stem] = load(path, known_cases, known_codes)
    report = {"coders": {name: {"cases_coded": len(cases),
                                "episodes": sum(len(e) for e in cases.values()),
                                "problems": problems[name]}
                         for name, cases in coders.items()},
              "pairs": {f"{x} vs {y}": agreement(coders[x], coders[y])
                        for x, y in combinations(coders, 2)},
              "candidate_codes": candidates(coders),
              "core_code_use": code_use(coders, known_codes)}
    run.write_json("agreement.json", report)
    run.log("coders_compared", coders=list(coders),
            problems=sum(len(p) for p in problems.values()))
    return report
