"""Model coding of interviews with the frozen codebook (version 1.0).

The model gets the same codebook and the same instructions as the human
coders (prompts/coder.md). It codes the whole interview, as qualitative coding
usually does: wherever a passage shows a code, it ticks the code and cites the
segments. Every tick names the story it belongs to: one thread of the founder's
journey, such as "the cafe order". The level-2 rules are then worked out story by
story, so codes from different stories are never combined. For every level-1
code the model gives a reason first and then its ticks (Dunivin 2025 found that
a reason before the decision raises agreement with people). It never quotes: the
words stay in the segments it cites.

Two ways to call the model, set by `calls` in [coding]:
  interview  one call per interview names the stories and codes every group
  group      one call names the stories; then one call per group across the
             whole interview, and a last call for anything no group asks about
Both see the whole codebook and the whole interview, so the only difference is
how much the model has to decide in one reply. Listing both runs both, and
round 1 compares them with the human coding.

A program then checks every entry. A code that does not belong where it was
given, a segment that does not exist, a tick with no segment or with a story
that was not named, or an anomaly with no reason is removed and recorded. A
code the model gave no decision on is recorded as undecided and left unticked.

Output, in the run folder under model_coding/<calls>/:
  coding.csv             every interview, one row per story, in the coding
                         page's own format, with the level-2 rules worked out
  pages/coding_*.csv     the same rows one interview per file, to open with
                         coding_page.py --load
  decisions/<case>.json  every reason and tick, ticked or not
  removed_entries.json   what the checks removed, and why
"""
import csv
import json
import re

from pydantic import BaseModel, ValidationError

from . import coding, model
from .runlog import HARNESS, ROOT, Run

CODEBOOK_NAME = "codebook version 1.0"
UNCLEAR = "unclear"
WHOLE = "whole journey"  # remarks that belong to no single story; level 1 only


class Tick(BaseModel):
    story: str
    segments: list[int]


class CodeDecision(BaseModel):
    code: str
    reason: str
    ticks: list[Tick]


class Anomaly(BaseModel):
    code: str
    story: str
    label: str
    why_no_code_fits: str
    segments: list[int]


class Story(BaseModel):
    name: str
    summary: str
    segments: list[int]
    search_state_reason: str
    search_state: str


class InterviewCoding(BaseModel):
    overview: str
    stories: list[Story]
    decisions: list[CodeDecision]
    anomalies: list[Anomaly]


class Stories(BaseModel):
    overview: str
    stories: list[Story]


class GroupCoding(BaseModel):
    decisions: list[CodeDecision]
    anomalies: list[Anomaly]


class SomethingElse(BaseModel):
    anomalies: list[Anomaly]


def load_codebook(run: Run) -> dict:
    """Level-1 groups, their codes, anomaly codes and the level-2 rules, from the frozen file."""
    return codebook_from(json.loads((ROOT / run.config()["coding"]["codebook"]).read_text(encoding="utf-8")))


def codebook_from(cb: dict) -> dict:
    """The same, from one codebook version's file."""
    codes = {c["id"]: c for c in cb["codes"]}
    anomalies = {"new" if a["id"].endswith("NEW") else a["overflows_from"]: a for a in cb["anomaly_codes"]}
    asks = {g["name"]: g["asks"] for g in cb["groups"]}
    groups = []
    for g in cb["levels"]["level1"]:
        name = g["group"]
        listed = g.get("codes") or sorted(
            (i for i, c in codes.items() if c["group"] == name and c.get("core") and i not in g.get("exclude", [])),
            key=lambda i: ([int(x) for x in re.findall(r"\d+", codes[i].get("added_in", "0"))], int(i.split("-")[1])))
        # A code added in a later version ("added_in") comes after the group's earlier codes, so their numbers stay.
        groups.append({"name": name, "title": g.get("name", name.capitalize()),
                       "asks": g.get("asks", asks.get(name, "")), "pick_one": g.get("pick_one"),
                       "codes": listed, "anomaly": None if name == "parts" else anomalies.get(name)})
    rules = [r for r in cb["levels"]["level2"] if r["kind"] != "judgment"]
    return {"version": cb["version"], "codes": codes, "groups": groups, "new": anomalies["new"],
            "rules": rules, "labels": {i: c["label"] for i, c in codes.items()}}


def code_line(c: dict) -> str:
    return (f"- {c['id']} | {c['label']} | Code it when: {c['applies_when']} | "
            f"Don't use it when: {c['does_not_apply_when']} | Meaning: {c.get('definition', '')}").replace("\n", " ")


def group_text(g: dict, cb: dict, n: int) -> str:
    lines = [f"Group {n}. {g['title']} ({g['name']}): {g['asks']}"]
    if g["pick_one"]:
        p = g["pick_one"]
        lines.append(f"{p['name']} (pick one, or \"{UNCLEAR}\"): {p['asks']}")
        lines += [code_line(cb["codes"][i]) for i in p["codes"]]
        lines.append("Then each of these:")
    lines += [code_line(cb["codes"][i]) for i in g["codes"]]
    if g["anomaly"]:
        a = g["anomaly"]
        lines.append(f"- {a['id']} | None of these fits | Use when: {a['applies_when']} | "
                     f"Don't use it when: {a['does_not_apply_when']}")
    return "\n".join(lines)


def system_prompt(cb: dict) -> str:
    blocks = [group_text(g, cb, n) for n, g in enumerate(cb["groups"], 1)]
    new = cb["new"]
    blocks.append(f"Something else: is there something relevant that no group asks about?\n"
                  f"- {new['id']} | Something no group asks about | Use when: {new['applies_when']} | "
                  f"Don't use it when: {new['does_not_apply_when']}")
    template = (HARNESS / "prompts" / "coder.md").read_text(encoding="utf-8")
    return template.replace("{codebook}", "\n\n".join(blocks)).replace("{new_id}", new["id"])


def task(name: str, cb: dict, **fields) -> str:
    text = (HARNESS / "prompts" / "coder_tasks" / f"{name}.md").read_text(encoding="utf-8")
    for k, v in {"new_id": cb["new"]["id"], **fields}.items():
        text = text.replace("{" + k + "}", v)
    return text


# ---- checks ----

class Checker:
    """Removes what does not hold up and records why."""

    def __init__(self, case_id: str, n_segments: int):
        self.case_id, self.n, self.removed = case_id, n_segments, []

    def note(self, where: str, problem: str) -> None:
        self.removed.append(f"{self.case_id} {where}: {problem}")

    def segments(self, where: str, numbers: list[int]) -> list[int]:
        bad = [s for s in numbers if not 1 <= s <= self.n]
        for s in bad:
            self.note(where, f"segment {s} does not exist")
        return sorted({s for s in numbers if 1 <= s <= self.n})

    def stories(self, given: list[Story], options: list[str]) -> list[dict]:
        out, seen = [], set()
        for st in given:
            name = st.name.strip()
            if not name or name.lower() == WHOLE or name in seen:
                self.note(f"story {name!r}", "empty, reserved or named twice; not counted")
                continue
            seen.add(name)
            state = st.search_state if st.search_state in options or st.search_state == UNCLEAR else UNCLEAR
            if state != st.search_state:
                self.note(f"story {name!r}", f"search state {st.search_state!r} is not one of the answers; recorded as {UNCLEAR}")
            out.append({"name": name, "summary": st.summary, "segments": self.segments(f"story {name!r}", st.segments),
                        "search_state": state, "search_state_reason": st.search_state_reason})
        return out

    def ticks(self, where: str, ticks: list[Tick], names: set[str]) -> list[dict]:
        out = []
        for t in ticks:
            story = t.story.strip()
            story = WHOLE if story.lower() == WHOLE else story
            segs = self.segments(where, t.segments)
            if story not in names and story != WHOLE:
                self.note(where, f"story {story!r} was not named; tick not counted")
            elif not segs:
                self.note(where, f"tick under {story!r} without a segment; not counted")
            else:
                out.append({"story": story, "segments": segs})
        return out

    def decisions(self, given: list[CodeDecision], expected: list[str], answered_elsewhere: set[str],
                  names: set[str]) -> list[dict]:
        """answered_elsewhere: search-state answers and anomaly codes, which have their own
        fields. A decision with no ticks for one of them says nothing and is dropped quietly;
        one with ticks is recorded."""
        out, seen = [], set()
        for d in given:
            if d.code in answered_elsewhere:
                if d.ticks:
                    self.note(d.code, "ticked as a code, but it is answered in its own field; not counted")
                continue
            if d.code not in expected:
                self.note(d.code, "is not a code of the codebook")
                continue
            if d.code in seen:
                self.note(d.code, "decided twice; the first decision is kept")
                continue
            seen.add(d.code)
            out.append({"code": d.code, "reason": d.reason, "ticks": self.ticks(d.code, d.ticks, names)})
        for code in expected:
            if code not in seen:
                self.note(code, "no decision given; left unticked")
                out.append({"code": code, "reason": "", "ticks": [], "undecided": True})
        return out

    def anomalies(self, given: list[Anomaly], allowed: set[str], names: set[str]) -> list[dict]:
        out = []
        for a in given:
            where = f"{a.code} ({a.story})"
            segs = self.segments(where, a.segments)
            story = WHOLE if a.story.strip().lower() == WHOLE else a.story.strip()
            if a.code not in allowed:
                self.note(where, "is not an anomaly code")
            elif story not in names and story != WHOLE:
                self.note(where, f"story {story!r} was not named; not counted")
            elif not a.why_no_code_fits.strip() or not segs:
                self.note(where, "without a reason or a segment; not counted")
            else:
                out.append({"code": a.code, "story": story, "label": a.label, "why": a.why_no_code_fits, "segments": segs})
        return out


def check_interview(chk: Checker, cb: dict, overview: str, stories: list[Story], decisions: list[CodeDecision],
                    anomalies: list[Anomaly]) -> dict:
    """The checked coding of one interview."""
    pick = cb["groups"][0]["pick_one"]["codes"]
    level1 = [i for g in cb["groups"] for i in g["codes"]]
    allowed = {g["anomaly"]["id"] for g in cb["groups"] if g["anomaly"]} | {cb["new"]["id"]}
    checked = chk.stories(stories, pick)
    names = {s["name"] for s in checked}
    return {"overview": overview, "stories": checked,
            "decisions": chk.decisions(decisions, level1, set(pick) | allowed, names),
            "anomalies": chk.anomalies(anomalies, allowed, names)}


def ticked_in(coded: dict, story: str) -> set[str]:
    """The codes ticked in one story, with its search-state answer: what the level-2 rules read."""
    out = {d["code"] for d in coded["decisions"] if any(t["story"] == story for t in d["ticks"])}
    state = next((s["search_state"] for s in coded["stories"] if s["name"] == story), UNCLEAR)
    return out | ({state} if state != UNCLEAR else set())


# ---- the two ways of calling ----

def reply(run: Run, key: str, system: str, user: str, schema, failed: list):
    """One call. A reply that is cut off or not in the requested form is recorded, not used."""
    record = model.call(run, "coder", key, system=system, user=user, schema=schema, cache_system=True)
    if record["response"]["stop_reason"] == "end_turn":
        try:
            return schema.model_validate_json(record["response"]["text"])
        except ValidationError:
            pass
    failed.append(key)
    return None


def numbered(segments: list[dict]) -> str:
    return "\n\n".join(f"[{k}] {s['text']}" for k, s in enumerate(segments, 1))


def by_interview(run, cb, system, case_id, segments, failed):
    """Returns (overview, stories, decisions, anomalies) or None."""
    user = task("interview", cb) + "\n\nThe interview:\n\n" + numbered(segments)
    got = reply(run, f"interview/{case_id}", system, user, InterviewCoding, failed)
    if got is None:
        return None
    return got.overview, got.stories, got.decisions, got.anomalies


def by_group(run, cb, system, case_id, segments, failed):
    # The interview goes into the instructions, which are cached, so the many
    # calls for one interview pay for it once at the full rate.
    system = system + "\n\nThe interview:\n\n" + numbered(segments)
    found = reply(run, f"group/{case_id}/stories", system, task("stories", cb), Stories, failed)
    if found is None:
        return None
    stories = "; ".join(f'"{s.name}" ({s.summary})' for s in found.stories) + f'; and "{WHOLE}"'
    decisions, anomalies = [], []
    for n, g in enumerate(cb["groups"], 1):
        got = reply(run, f"group/{case_id}/{g['name']}", system,
                    task("group", cb, stories=stories, group=f"Group {n}, {g['title']}"), GroupCoding, failed)
        if got:
            decisions += got.decisions
            anomalies += got.anomalies
    got = reply(run, f"group/{case_id}/something-else", system, task("something_else", cb, stories=stories),
                SomethingElse, failed)
    if got:
        anomalies += got.anomalies
    return found.overview, found.stories, decisions, anomalies


# ---- rows in the coding page's format ----

def met(rule: dict, ticked: set) -> bool:
    """All of 'all' ticked, one of 'any' if given, none of 'none' (levels.json)."""
    return (all(c in ticked for c in rule.get("all", []))
            and (not rule.get("any") or any(c in ticked for c in rule["any"]))
            and not any(c in ticked for c in rule.get("none", [])))


def columns(cb: dict) -> list[str]:
    rules = [r["id"].lower().replace("-", "_", 1) for r in cb["rules"]]
    return (["case_no", "case_id", "coder", "codebook", "story", "story_name", "segments", "summary"]
            + [g["name"] for g in cb["groups"]] + ["anomaly_codes", "anomaly_notes"] + rules + ["notes", "evidence"])


def segs_text(segs: list[int]) -> str:
    return ", ".join(f"s{s:02d}" for s in segs)


def rows_for(cb: dict, base: dict, coded: dict) -> list[dict]:
    """One row per story, then one for the whole journey if anything was ticked there.
    The level-2 rules are worked out per story; the whole-journey row has none."""
    names = [s["name"] for s in coded["stories"]]
    uses_whole = any(t["story"] == WHOLE for d in coded["decisions"] for t in d["ticks"]) \
        or any(a["story"] == WHOLE for a in coded["anomalies"])
    if not names and not uses_whole:
        return [{**base, "story": 0, "notes": coded["overview"]}]
    rows = []
    for k, name in enumerate(names + ([WHOLE] if uses_whole else []), 1):
        st = next((s for s in coded["stories"] if s["name"] == name), None)
        ticked = ticked_in(coded, name)
        segs = sorted({x for d in coded["decisions"] for t in d["ticks"] if t["story"] == name for x in t["segments"]}
                      | set(st["segments"] if st else []))
        row = {**base, "story": k if st else "W", "story_name": name, "segments": ", ".join(map(str, segs)),
               "summary": st["summary"] if st else "Remarks that belong to no single story"}
        for g in cb["groups"]:
            order = (g["pick_one"]["codes"] if g["pick_one"] else []) + g["codes"]
            row[g["name"]] = "; ".join(c for c in order if c in ticked)
        anos = [a for a in coded["anomalies"] if a["story"] == name]
        row["anomaly_codes"] = "; ".join(a["code"] for a in anos)
        row["anomaly_notes"] = " | ".join(f"{a['code']}: {a['label']}: {a['why']} ({segs_text(a['segments'])})" for a in anos)
        for r in cb["rules"]:
            row[r["id"].lower().replace("-", "_", 1)] = ("yes" if met(r, ticked) else "no") if st else ""
        reasons = [f"search state {st['search_state']}: {st['search_state_reason']}"] if st else []
        reasons += [f"{d['code']} ({segs_text([x for t in d['ticks'] if t['story'] == name for x in t['segments']])}): {d['reason']}"
                    for d in coded["decisions"] if any(t["story"] == name for t in d["ticks"])]
        row["notes"] = "Model's reasons for its ticks. " + " | ".join(reasons)
        row["evidence"] = ""
        rows.append(row)
    return rows


def write_csv(path, cols, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def code_interview(run: Run, cb: dict, system: str, calls: str, case_no: str, case_id: str,
                   segments: list[dict], failed: list) -> tuple[list[dict], list[str], dict | None]:
    """Code one interview one way; returns its rows, what was removed, and every decision."""
    got = (by_interview if calls == "interview" else by_group)(run, cb, system, case_id, segments, failed)
    if got is None:
        return [], [], None
    chk = Checker(case_id, len(segments))
    coded = check_interview(chk, cb, *got)
    coder = "model:" + run.config()["models"]["coder"]["model"]
    base = {"case_no": case_no, "case_id": case_id, "coder": coder, "codebook": CODEBOOK_NAME}
    return rows_for(cb, base, coded), chk.removed, coded


def build(run: Run) -> dict:
    cfg = run.config()["coding"]
    calls_list = cfg.get("calls", "interview")
    calls_list = [calls_list] if isinstance(calls_list, str) else calls_list
    cases = coding.eligible_cases(run)
    if cfg["model_sample"]:
        cases = cases[:cfg["model_sample"]]  # the first interviews in worksheet order
    cb = load_codebook(run)
    system = system_prompt(cb)
    cols = columns(cb)
    summary = {}
    for calls in calls_list:
        out = run.dir / "model_coding" / calls
        rows, removed, failed = [], [], []
        for n, case in enumerate(cases, 1):
            segments = [json.loads(line) for line in
                        open(run.dir / "segments" / f"{case['case_id']}.jsonl", encoding="utf-8")]
            new_rows, new_removed, decisions = code_interview(
                run, cb, system, calls, f"{n:03d}", case["case_id"], segments, failed)
            if decisions is None:
                continue
            rows += new_rows
            removed += new_removed
            run.write_json(f"model_coding/{calls}/decisions/{case['case_id']}.json", decisions)
            coder = new_rows[0]["coder"].replace(":", "-")
            write_csv(out / "pages" / f"coding_{n:03d}_{case['case_id']}_{coder}.csv", cols, new_rows)
        write_csv(out / "coding.csv", cols, rows)
        run.write_json(f"model_coding/{calls}/removed_entries.json", removed)
        log = [json.loads(l) for l in open(run.log_path, encoding="utf-8")]
        cost = sum(e.get("cost_usd", 0) for e in log
                   if e["event"] == "model_call" and e["key"].startswith(calls + "/"))
        summary[calls] = {"interviews": len(cases), "not_completed": sorted({f.split("/")[1] for f in failed}),
                          "calls_failed": len(failed), "stories": sum(1 for r in rows if r["story"] not in (0, "W")),
                          "interviews_without_story": sum(1 for r in rows if r["story"] == 0),
                          "entries_removed": len(removed), "cost_usd": round(cost, 4)}
        run.log("model_coding_built", model=run.config()["models"]["coder"]["model"], calls=calls,
                codebook=cfg["codebook"], codebook_version=cb["version"], **summary[calls])
    return summary
