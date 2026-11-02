"""Check that every quote in a codebook's evidence file is in the paper it cites.

Usage: python -m serendipity_harness.evidence EVIDENCE_JSON

The evidence file lists, for each code added or revised in a codebook version, a
sentence from each paper that states it, with its page and the Markdown reading
copy of the paper ("text": a path from the project root, or from ~ for the
literature library). A quote counts as found when its words appear in that text
in order, ignoring case, punctuation, line breaks, hyphenation and the
ligatures and stray bytes that PDF conversion leaves. Prints each quote with
"found" or "MISSING" and exits non-zero if any is missing.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from .runlog import ROOT


def words(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).replace("\x00", "")
    s = re.sub(r"-\s*\n\s*", "", s)
    s = re.sub(r"(\w) - (\w)", r"\1\2", s)
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def check(path: Path) -> list[tuple[str, str, bool]]:
    ev = json.loads(path.read_text(encoding="utf-8"))
    texts, out = {}, []
    for code, items in ev["codes"].items():
        for e in items:
            src = Path(e["text"]).expanduser() if e["text"].startswith("~") else ROOT / e["text"]
            if src not in texts:
                texts[src] = words(src.read_text(encoding="utf-8", errors="replace")) if src.exists() else ""
            body = texts[src]
            found = words(e["quote"]) in body or words(e["quote"]).replace(" ", "") in body.replace(" ", "")
            out.append((code, f"{e['paper']} p. {e['page']}", found))
    return out


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    res = check(Path(sys.argv[1]))
    for code, ref, ok in res:
        print(f"{'found  ' if ok else 'MISSING'}  {code:14} {ref}")
    missing = sum(not ok for *_, ok in res)
    print(f"{len(res) - missing} of {len(res)} quotes found")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
