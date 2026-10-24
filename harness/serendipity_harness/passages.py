"""Stage 2: passages with stable identifiers.

Each page is cut into passages of roughly equal size at sentence ends. A
passage is always an exact slice of the saved page text, so any quotation the
harness later shows can be copied from the source rather than typed by a model.

Passage identifier: <paper_id>:p<PDF page>:<number>, e.g. dew2009-1a2b3c:p015:02
"""
import json
import re

from .runlog import Run

SENTENCE_END = re.compile(r"(?<=[.!?])[\"')\]]*\s+")


def split_page(text: str, target: int) -> list[tuple[int, int]]:
    """Return (start, end) character offsets that cover the page without gaps."""
    cuts, start = [], 0
    while len(text) - start > target * 1.5:
        ends = [m.end() for m in SENTENCE_END.finditer(text, start + target // 2, start + target * 3 // 2)]
        cut = min(ends, key=lambda e: abs(e - (start + target))) if ends else start + target
        cuts.append((start, cut))
        start = cut
    if text[start:].strip():
        cuts.append((start, len(text)))
    return cuts


def build(run: Run) -> int:
    target = run.config()["extraction"]["passage_chars"]
    total = 0
    for paper in run.read_json("inventory.json"):
        if paper["duplicate_of"]:
            continue
        pid = paper["paper_id"]
        pages = run.read_json(f"pages/{pid}.json")["pages"]
        out = run.dir / "passages" / f"{pid}.jsonl"
        out.parent.mkdir(exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for page_no, text in enumerate(pages, 1):
                for k, (a, b) in enumerate(split_page(text, target), 1):
                    f.write(json.dumps({"passage_id": f"{pid}:p{page_no:03d}:{k:02d}",
                                        "paper_id": pid, "pdf_page": page_no,
                                        "char_start": a, "char_end": b,
                                        "text": text[a:b]}, ensure_ascii=False) + "\n")
                    total += 1
    run.log("passages_built", passages=total, target_chars=target)
    return total
