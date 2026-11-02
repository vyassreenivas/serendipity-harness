"""The two levels of the codebook, read from harness/codebook/levels.json.

Level 1 is what coders tick, by group; level 2 is worked out afterwards.
Every page (short codebook, coding page, trail) reads the levels through these
functions, so they always agree.
"""
from __future__ import annotations

import json
from pathlib import Path

from export import GROUPS, H, L2_SOURCES, LEVELS, MISFIT as ANOMALY
from workbook import cite, evidence_for

ASKS = {name: asks for name, _sq, asks in GROUPS}
ANOMALY_BY_GROUP = {m.get("overflows_from") or "new": m for m in ANOMALY["codes"]}
NEW = ANOMALY_BY_GROUP.get("new") or next(m for m in ANOMALY["codes"] if m["id"].endswith("NEW"))


# The sub-questions in full, as on the research-question page, and the core papers (paper list).
SUB_QUESTIONS = {"SQ" + r["sq"]: r["text"] for r in json.loads(Path(__file__).with_name("questions.json").read_text(encoding="utf-8"))["rows"]}
CORE_PAPERS = {c["short"] for c in json.loads((H / "codebook" / "core_papers.json").read_text(encoding="utf-8"))["papers"]}


def level1(state: dict, draft: dict) -> list[dict]:
    """The groups coders answer, each with its codes (core codes of that group unless listed),
    an optional pick-one question, and its anomaly code."""
    groups = []
    for g in LEVELS["level1"]:
        name = g["group"]
        codes = g.get("codes") or sorted(
            (i for i in draft if draft[i]["group"] == name and state[i]["Status"] == "core" and i not in g.get("exclude", [])),
            key=lambda i: ([int(x) for x in draft[i].get("added_in", "0").split(".")], int(i.split("-")[1])))
        # a code added in a later version comes after the group's earlier codes, so their numbers stay
        anomaly = None if name == "parts" else ANOMALY_BY_GROUP.get(name)
        groups.append({"group": name, "sq": g["sq"], "name": g.get("name", name.capitalize()),
                       "asks": g.get("asks", ASKS.get(name, "")), "pick_one": g.get("pick_one"),
                       "codes": codes, "anomaly": anomaly})
    return groups


def level1_ids(state: dict, draft: dict) -> list[str]:
    return [c for g in level1(state, draft) for c in (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]]


def met(rule: dict, ticked: set) -> bool:
    """A rule is met when all of 'all' are ticked, one of 'any' (if given), and none of 'none'."""
    return (all(c in ticked for c in rule.get("all", []))
            and (not rule.get("any") or any(c in ticked for c in rule["any"]))
            and not any(c in ticked for c in rule.get("none", [])))


def rule_text(rule: dict, label: dict) -> str:
    """The rule in words, using the codes' labels."""
    parts = [label[c] for c in rule.get("all", [])]
    if rule.get("any"):
        parts.insert(0, " or ".join(label[c] for c in rule["any"]))
    text = " + ".join(parts)
    if rule.get("none"):
        text += (", without " if text else "Without ") + " or ".join(label[c] for c in rule["none"])
    return text


def numbers(state: dict, draft: dict) -> dict:
    """Each level-1 code's number by group, as in the codebook document: 2.3 is the third code of group 2."""
    num = {}
    for gi, g in enumerate(level1(state, draft), 1):
        for k, c in enumerate((g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"], 1):
            num[c] = f"{gi}.{k}"
    return num


def rule_equation(rule: dict, label: dict, num: dict) -> str:
    """The rule as a code equation over numbered level-1 codes, with AND, OR and NOT."""
    part = lambda c: f"{label[c]} ({num[c]})"
    terms = [" AND ".join(part(c) for c in rule.get("all", []))] if rule.get("all") else []
    if rule.get("any"):
        terms.append("(" + " OR ".join(part(c) for c in rule["any"]) + ")")
    text = " AND ".join(terms)
    if rule.get("none"):
        text += (" AND " if text else "") + " AND ".join("NOT " + part(c) for c in rule["none"])
    return text


def rule_evidence(rule: dict, draft: dict) -> list[dict]:
    """The papers behind a level-2 item: its own sentences, or the chosen evidence of the codes it came from,
    less the works level2_sources.json drops and plus the sentences it adds."""
    if "evidence" in rule:
        return [dict(cite(q["passage_id"].split(":")[0]), quote=q) for q in rule["evidence"]]
    out, seen = [], set()
    drop = set(L2_SOURCES["drop"].get(rule["id"], []))
    for cid in rule.get("evidence_from", []):
        for e in evidence_for(draft[cid]):
            if e["chosen"] and not e.get("none") and e["short"] not in drop and e["short"] + e["url"] not in seen:
                seen.add(e["short"] + e["url"])
                out.append(e)
    for q in L2_SOURCES["add"].get(rule["id"], []):  # sentences already held that state the item better
        out.append(dict(cite(q["passage_id"].split(":")[0]), quote=q, chosen=True, close=False))
    return out
