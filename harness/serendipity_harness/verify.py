"""Stage 4: quotation check.

For every code in the codebook, look for its supporting quotation in the page
text of the PDF it is attributed to, and report how strictly it matches and on
which PDF page. No model is involved.

Match levels, strictest first:
  exact        character for character
  typographic  after normalising spacing, line-break hyphens, ligatures,
               quotation marks and dashes
  case         as typographic, also ignoring capital letters
  loose        ignoring case, punctuation and spacing
  not_found    none of the above

A match shows that the words are in the paper. It does not show that the
passage supports the coding rule; that judgment belongs to the researcher.
"""
from bisect import bisect_right
from pathlib import Path
import csv
import json
import re

from .runlog import ROOT, Run, sha256

LEVELS = ["exact", "typographic", "case", "loose", "not_found"]
LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
MARKS = {"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "}
ELLIPSIS = re.compile(r"\[\s*(?:\.\.\.|…)\s*\]|\.\.\.|…")
MIN_FRAGMENT = 8  # letters and digits; shorter fragments are too short to locate


def typographic(s: str) -> str:
    for a, b in {**LIGATURES, **MARKS}.items():
        s = s.replace(a, b)
    s = re.sub(r"-\s*\n\s*", "", s)
    return re.sub(r"\s+", " ", s).strip()


def loose(s: str) -> str:
    for a, b in LIGATURES.items():
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


class PaperText:
    """Page text of one paper in three normalisations, each searchable by page."""

    def __init__(self, pages: list[str]):
        self.views = {}
        for level, norm, joiner in (("exact", lambda s: s, "\n"),
                                    ("typographic", typographic, " "),
                                    ("case", lambda s: typographic(s).lower(), " "),
                                    ("loose", loose, "")):
            parts = [norm(p) for p in pages]
            starts, pos = [], 0
            for part in parts:
                starts.append(pos)
                pos += len(part) + len(joiner)
            self.views[level] = (norm, joiner.join(parts), starts)

    def find(self, fragment: str) -> tuple[str, int | None, int | None]:
        """Return (level, PDF page, position in the loose view)."""
        found_level, page = "not_found", None
        for level in LEVELS[:-1]:
            norm, text, starts = self.views[level]
            at = text.find(norm(fragment))
            if at >= 0:
                found_level, page = level, bisect_right(starts, at)
                break
        norm, text, _ = self.views["loose"]
        at = text.find(norm(fragment))
        return found_level, page, (at if at >= 0 else None)


def check_quote(quote: str, paper: PaperText) -> dict:
    fragments = [f.strip() for f in ELLIPSIS.split(quote) if len(loose(f)) >= MIN_FRAGMENT]
    results, positions = [], []
    for fragment in fragments:
        level, page, at = paper.find(fragment)
        results.append({"fragment": fragment, "level": level, "pdf_page": page})
        positions.append(at)
    if not results:
        return {"level": "not_found", "pdf_pages": [], "elided": False,
                "fragments_in_order": None, "fragments": []}
    weakest = max((r["level"] for r in results), key=LEVELS.index)
    located = [p for p in positions if p is not None]
    return {"level": weakest,
            "pdf_pages": sorted({r["pdf_page"] for r in results if r["pdf_page"]}),
            "elided": len(results) > 1,
            "fragments_in_order": located == sorted(located) if len(located) == len(results) else None,
            "fragments": results}


def build(run: Run) -> dict:
    cfg = run.config()
    codebook_path = ROOT / cfg["inputs"]["codebook"]
    codebook = json.loads(codebook_path.read_text(encoding="utf-8"))
    by_stem = {Path(p["file"]).stem: p for p in run.read_json("inventory.json")}
    texts: dict[str, PaperText] = {}

    rows = []
    for code in codebook["codes"]:
        v3 = code["original_v3"]
        row = {"code_id": code["id"], "label": code["editorial"]["label"],
               "quote_source": v3.get("quote_source"), "quote": v3.get("quote") or "",
               "paper_id": None, "level": "not_found", "pdf_pages": [], "elided": False,
               "fragments_in_order": None, "low_text_page": False, "note": ""}
        paper = by_stem.get(row["quote_source"] or "")
        if not row["quote"]:
            row["note"] = "code has no quotation"
        elif paper is None:
            row["note"] = "source PDF not in papers folder"
        elif paper["error"]:
            row["note"] = "source PDF could not be read"
        else:
            pid = row["paper_id"] = paper["paper_id"]
            if pid not in texts:
                texts[pid] = PaperText(run.read_json(f"pages/{pid}.json")["pages"])
            result = check_quote(row["quote"], texts[pid])
            row.update({k: result[k] for k in ("level", "pdf_pages", "elided", "fragments_in_order")})
            row["fragments"] = result["fragments"]
            # Text from a page with little readable text may be poor OCR.
            row["low_text_page"] = bool(set(row["pdf_pages"]) & set(paper["low_text_pages"]))
        rows.append(row)

    counts = {level: sum(1 for r in rows if r["level"] == level) for level in LEVELS}
    summary = {"scope": "Checks that quoted words occur in the attributed PDF. "
                        "Does not check that a quotation supports its code.",
               "codebook": cfg["inputs"]["codebook"], "codebook_sha256": sha256(codebook_path),
               "codes": len(rows), "by_level": counts,
               "elided_quotes": sum(1 for r in rows if r["elided"]),
               "out_of_order": [r["code_id"] for r in rows if r["fragments_in_order"] is False],
               "not_found": [r["code_id"] for r in rows if r["level"] == "not_found"]}
    run.write_json("quote_check.json", {"summary": summary, "quotes": rows})

    with open(run.dir / "quote_check.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["code_id", "label", "level", "pdf_pages", "elided", "fragments_in_order",
                  "low_text_page", "note", "quote_source", "quote"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({**r, "pdf_pages": " ".join(map(str, r["pdf_pages"]))})

    run.log("quotes_checked", **{k: summary[k] for k in ("codes", "by_level", "codebook_sha256")})
    return summary
