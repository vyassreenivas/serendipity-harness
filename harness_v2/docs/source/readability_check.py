"""Check a Word file for plain-English readability.

Usage: python readability_check.py ../technical_document.docx

Reports sentences over 30 words, paragraphs over 7 sentences, and the average
sentence length (plain-English guidance aims for about 15 to 20 words).
Skips headings, table cells and the References section. Quoted text counts
as one word.
"""
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_SENTENCE, MAX_PARAGRAPH = 30, 7


def paragraphs(path):
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    in_tables = {id(p) for tc in root.iter(W + "tc") for p in tc.iter(W + "p")}
    for p in root.iter(W + "p"):
        if id(p) in in_tables:  # table cells hold lists, not running prose
            continue
        text = "".join(t.text or "" for t in p.iter(W + "t")).strip()
        style = p.find(f"{W}pPr/{W}pStyle")
        yield text, (style.get(W + "val") if style is not None else "")


def sentences(text):
    text = re.sub(r"\"[^\"]*\"|“[^”]*”|`[^`]*`", "Q", text)
    text = re.sub(r"\b(e\.g|i\.e|et al|pp|vol|no|Eds|ed)\.", r"\1", text)
    text = re.sub(r"^(Figure|Table) (\d+)\.\s*", r"\1 \2 ", text)
    return [s for s in re.split(r"(?<=[.?!])\s+(?=[A-Z0-9(])", text) if s.strip()]


def main(path):
    lengths, findings, in_refs = [], [], False
    for text, style in paragraphs(path):
        if style.startswith("Heading"):
            in_refs = text == "References"
            continue
        if in_refs or not text:
            continue
        sents = sentences(text)
        if len(sents) > MAX_PARAGRAPH:
            findings.append(f"paragraph of {len(sents)} sentences | {text[:80]}")
        for s in sents:
            n = len(re.findall(r"[A-Za-z0-9’'-]+", s))
            lengths.append(n)
            if n > MAX_SENTENCE:
                findings.append(f"sentence of {n} words | {s[:100]}")
    print("\n".join(findings) or "No long sentences or paragraphs.")
    print(f"\n{len(lengths)} sentences; average {sum(lengths) / len(lengths):.1f} words; "
          f"{sum(1 for n in lengths if n > 25)} over 25 words")


if __name__ == "__main__":
    main(sys.argv[1])
