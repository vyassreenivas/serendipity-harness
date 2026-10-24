"""Stage 1: paper inventory and page text.

Reads every PDF in the papers folder, gives it a stable identifier, saves the
text of each page, and flags pages with too little readable text.
"""
import importlib.metadata
import re

from pypdf import PdfReader

from .runlog import ROOT, Run, sha256


def paper_id(filename: str, digest: str) -> str:
    """'Dew - 2009 - Serendipity in Entrepreneurship.pdf' -> 'dew2009-1a2b3c'.

    The hash suffix keeps the identifier stable if the file is renamed and
    distinct if two versions of the same paper are present.
    """
    author, _, rest = filename.partition(" - ")
    year = re.search(r"\d{4}", rest)
    first_author = re.split(r" and | et al", author)[0]
    surname = re.sub(r"[^a-z]", "", first_author.lower()) or "paper"
    return f"{surname}{year.group() if year else ''}-{digest[:6]}"


def build(run: Run) -> list[dict]:
    cfg = run.config()
    papers_dir = ROOT / cfg["inputs"]["papers_dir"]
    min_chars = cfg["extraction"]["min_chars_per_page"]
    extractor = f"pypdf {importlib.metadata.version('pypdf')}"

    papers, first_seen = [], {}
    for pdf in sorted(papers_dir.glob("*.pdf")):
        digest = sha256(pdf)
        pid = paper_id(pdf.name, digest)
        record = {"paper_id": pid, "file": str(pdf.relative_to(ROOT)), "sha256": digest,
                  "extractor": extractor, "pages": 0, "low_text_pages": [], "error": None,
                  # the same file saved under two names counts as one paper
                  "duplicate_of": first_seen.get(digest)}
        first_seen.setdefault(digest, record["file"])
        try:
            pages = [page.extract_text() or "" for page in PdfReader(pdf).pages]
        except Exception as exc:  # an unreadable file is reported, not skipped silently
            record["error"] = f"{type(exc).__name__}: {exc}"
            pages = []
        record["pages"] = len(pages)
        record["low_text_pages"] = [n for n, text in enumerate(pages, 1)
                                    if len(re.sub(r"\s", "", text)) < min_chars]
        run.write_json(f"pages/{pid}.json", {"paper_id": pid, "pages": pages})
        papers.append(record)

    run.write_json("inventory.json", papers)
    run.log("inventory_built", papers=len(papers),
            duplicate_files=sum(1 for p in papers if p["duplicate_of"]),
            unreadable_files=sum(1 for p in papers if p["error"]),
            papers_with_low_text_pages=sum(1 for p in papers if p["low_text_pages"]),
            extractor=extractor)
    return papers
