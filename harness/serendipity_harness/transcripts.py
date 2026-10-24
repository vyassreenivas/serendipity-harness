"""Interview inventory and segments.

Lists every interview transcript, gives it a stable identifier, and cuts it
into segments (one per question or answer paragraph). A segment is an exact
slice of the transcript, so a coded excerpt can be copied from the source
rather than typed by a model.

Segment identifier: <case_id>:s<number>, e.g. airtulip-1a2b3c:s07
"""
import json
import re

from .runlog import ROOT, Run, sha256

PARAGRAPH = re.compile(r"\S(?:.*\S)?(?:\n(?!\s*\n).*\S)*")  # text up to a blank line
RULE = re.compile(r"^=+$")


def segment(text: str) -> list[dict]:
    segments, in_header = [], False
    for m in PARAGRAPH.finditer(text):
        body = m.group()
        lines = body.split("\n")
        if RULE.match(lines[0]):
            in_header = not RULE.match(lines[-1]) or len(lines) == 1
            role = "header"
        elif in_header:
            role, in_header = "header", not RULE.match(lines[-1])
        else:
            role = {"Q:": "question", "A:": "answer"}.get(body[:2], "other")
        segments.append({"role": role, "char_start": m.start(), "char_end": m.end(), "text": body})
    return segments


def build(run: Run) -> list[dict]:
    cfg = run.config()["inputs"]
    folder = ROOT / cfg["transcripts_dir"]
    names = (ROOT / cfg["transcripts_manifest"]).read_text(encoding="utf-8").split("\n")
    names = [n.strip() for n in names if n.strip()]

    cases = []
    for name in names:
        path = folder / name
        record = {"case_id": None, "file": str(path.relative_to(ROOT)), "sha256": None,
                  "words": 0, "segments": 0, "answers": 0, "error": None}
        if not path.exists():
            record["error"] = "file listed in manifest but not found"
            cases.append(record)
            continue
        digest = sha256(path)
        text = path.read_text(encoding="utf-8")
        case_id = f"{path.stem[:40].rstrip('-')}-{digest[:6]}"
        segments = segment(text)
        for k, seg in enumerate(segments, 1):
            seg["segment_id"] = f"{case_id}:s{k:02d}"
        record.update(case_id=case_id, sha256=digest, words=len(text.split()),
                      segments=len(segments),
                      answers=sum(1 for s in segments if s["role"] == "answer"))
        out = run.dir / "segments" / f"{case_id}.jsonl"
        out.parent.mkdir(exist_ok=True)
        out.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in segments),
                       encoding="utf-8")
        cases.append(record)

    run.write_json("cases.json", cases)
    run.log("transcripts_inventoried", cases=len(cases),
            missing=sum(1 for c in cases if c["error"]),
            segments=sum(c["segments"] for c in cases),
            words=sum(c["words"] for c in cases))
    return cases
