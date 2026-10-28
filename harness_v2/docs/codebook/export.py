"""Export the pilot codebook for the readable document.

Usage: python export.py codebook.json
Reads the suggested (or final) review sheet and the draft from the version 1
harness, the source metadata, and the anomaly codes; writes one JSON file the
document builder reads. Contains no interview text.
"""
from __future__ import annotations
import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

H = Path(__file__).resolve().parents[3] / "harness"
REVIEW = H / "codebook" / ("review.csv" if (H / "codebook" / "review.csv").exists() else "review_suggested.csv")
DRAFT = H / "runs" / "20261012-124904" / "codebook_draft.json"
META = json.loads((H / "codebook" / "paper_metadata.json").read_text(encoding="utf-8"))
MISFIT = json.loads((H / "codebook" / "anomaly_codes.json").read_text(encoding="utf-8"))
# Papers quoted under each code (most supporting passages first); the rest are listed.
QUOTED = 5
# Reading order inside a group where the order carries meaning.
ORDER = {"definition-09": 1, "definition-07": 2, "definition-13": 3, "definition-04": 4}
# Years as cited elsewhere in the project (issue year, not online-first year).
AUTHOR = {"hargadon1997-2239c7": "Hargadon and Sutton", "austin2012-0c5916": "Austin et al"}  # file name gives too few authors
YEAR = {"Busch": 2024, "Brownell et al": 2024, "Reijonen and Heroum": 2026, "Oo et al": 2025}

GROUPS = [  # sub-question order, as in Stage 1
    ("definition", "SQ1", "Does this episode count as serendipity?"),
    ("type", "SQ1", "What kind of serendipity is it?"),
    ("rival", "SQ1", "What else could explain the same story?"),
    ("trigger", "SQ2", "What unexpected event started it?"),
    ("background", "SQ3", "What did the founder already have?"),
    ("mechanism", "SQ3", "What did the founder do to turn it into something?"),
    ("role", "SQ4", "What part did it play in the venture?"),
    ("outcome", "SQ4", "What came of it?"),
    ("condition", "SQ5", "What made it easier or harder?"),
    ("account", "SQ6", "How does the founder tell it afterwards?"),
    ("anomaly", "all", "What in this episode does no other code capture?"),
]


PASSAGES = H / "runs" / "20261012-124904" / "passages"
ADDED = json.loads((H / "codebook" / "added_papers.json").read_text(encoding="utf-8")) \
    if (H / "codebook" / "added_papers.json").exists() else {"maps": [], "new_codes": []}
LEVELS = json.loads((H / "codebook" / "levels.json").read_text(encoding="utf-8"))  # what coders tick; what is worked out
L2_SOURCES = json.loads((H / "codebook" / "level2_sources.json").read_text(encoding="utf-8"))  # level-2 sources read against each rule
PASSAGE_DIRS = [PASSAGES] + ([H / "runs" / ADDED["run"] / "passages"] if ADDED.get("run") else [])
STOP = set("""a an the and or of to in on for with by as at from that this these those is are was were be been being it its
their they them he she his her we our you your i not no but if then than so such which who whom what when where while also
into out about over more most other some any can may might would could should will one two has have had do does did""".split())
BOILER = re.compile(r"downloaded|jstor|copyright|©|https?://|all rights reserved|terms and conditions|licen[cs]e|\bdoi\b", re.I)
_passages: dict[str, dict] = {}


def passage(pid: str) -> dict | None:
    """The passage, or None where the papers are not on this computer (they are never in the repository)."""
    paper = pid.split(":")[0]
    if paper not in _passages:
        _passages[paper] = {}
        folder = next((d for d in PASSAGE_DIRS if (d / f"{paper}.jsonl").exists()), None)
        for line in (open(folder / f"{paper}.jsonl", encoding="utf-8") if folder else []):
            rec = json.loads(line)
            _passages[paper][rec["passage_id"]] = rec
    return _passages[paper].get(pid)


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2 and w not in STOP]


def sentences(text: str) -> list[str]:
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # join words split across lines
    text = text.translate({0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl"})
    text = re.sub(r"\s+", " ", text).strip()
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'‘“(])", text)]


# Words that open a sentence; one glued straight onto a few earlier words with no
# punctuation between marks a section heading the PDF ran into the sentence.
STARTERS = set("""The This These That Those We Our In It Its A An As For However Thus When While Although
Next Such One Here Yet But First Second Third Finally Moreover Furthermore To By From Unlike Instead
Rather Given Despite Building Drawing Following Using Prior Recent Serendipity Entrepreneurs Founders
Firms Research Scholars Studies Most Many Some Each Both All Only Because Since If Whereas Overall""".split())
CITATION = re.compile(r"\([^()]*\b(?:19|20)\d\d[a-z]?\b[^()]*\)")


def tidy(sent: str) -> str | None:
    """Make a sentence fit to quote, or reject it. Rules, in order:
    1. A section heading run into the sentence ("Generating contingency to harvest
       serendipity Next to ...") is cut off: the text is kept from the opening word.
    2. Fragments are dropped: text that starts mid-sentence (lower-case first letter)
       or stops on a colon, semicolon or comma, or leaves a bracket open.
    3. Citation-only text is dropped: fewer than 8 words left once the bracketed
       references, e.g. (Dew, 2009), are taken out.
    4. Text the PDF mangled is dropped: words run together into one 25-letter token,
       or figure and table labels (two or more colons).
    The kept text is always a stretch of the paper's own words; nothing is rewritten."""
    words_ = sent.split()
    for i in range(1, min(len(words_), 11)):
        prev, w = words_[i - 1], words_[i]
        if w in STARTERS and re.fullmatch(r"[A-Za-z\-]+|[\d.|]+", prev) and words_[0][:1].isupper() | words_[0][:1].isdigit():
            if all(re.fullmatch(r"[A-Za-z\-]+|[\d.|]+", x) for x in words_[:i]) and prev.lower() not in FUNCTION:
                sent = " ".join(words_[i:])
            break
    first = re.search(r"[A-Za-z]", sent)
    if not first or first.group().islower() or sent.rstrip()[-1:] in ":;," or sent.count("(") != sent.count(")"):
        return None
    if len(CITATION.sub("", sent).split()) < 8:
        return None
    if re.search(r"[A-Za-z]{25,}", sent) or sent.count(":") >= 2:  # glued words; figure or table labels
        return None
    return sent


def best_sentence(code: dict, pids: list[str]) -> dict | None:
    """Fixed rule: among the sentences of the passages cited for this code in this paper,
    pick the one sharing the most distinctive words with the code's draft wording
    (label, definition, applies_when). Sentences of 8 to 45 words only, made fit to quote
    by tidy(); boilerplate and citation lists excluded. Ties go to the earlier sentence."""
    target = Counter(words(" ".join([code["label"], code["definition"], code["applies_when"]])))
    best = None
    for pid in pids:
        rec = passage(pid)
        if rec is None:
            continue
        for sent in sentences(rec["text"]):
            sent = tidy(sent)
            if sent is None:
                continue
            n = len(sent.split())
            if not 8 <= n <= 45 or BOILER.search(sent) or len(re.findall(r"\b(19|20)\d\d\b", sent)) > 2:
                continue
            ws = set(words(sent))
            score = sum(1 + math.log(target[w]) for w in ws if w in target) / math.sqrt(len(ws) or 1)
            if best is None or score > best[0]:
                best = (score, sent, pid, rec["pdf_page"])
    if best is None:
        return None
    return {"text": repair(best[1]), "passage_id": best[2], "pdf_page": best[3]}


MD_DIRS = [H.parent / "papers" / "md"]
LIBRARY = Path.home() / "Projects" / "litreview" / "library" / "papers"
_md_cache: dict[str, list[tuple[str, str, list[int]]]] = {}
_lib_by_doi: dict[str, Path] | None = None


def _strip_markdown(t: str) -> str:
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)          # images
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)       # links: keep the text
    t = re.sub(r"</?(sup|sub|br|i|b|em|strong)[^>]*>", " ", t)
    t = re.sub(r"(\*\*|__|\*|`)", "", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.M)
    t = t.translate({0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl", 0x00AD: None})
    return re.sub(r"\s+", " ", t)


def _md_texts(paper_id: str) -> list[tuple[str, str, list[int]]]:
    """Clean Markdown versions of a paper: the literature library's copy found by DOI, then
    the project's papers/md file with the PDF's name. Each comes with a letters-and-digits key
    and a map from key position back to the text."""
    global _lib_by_doi
    if paper_id in _md_cache:
        return _md_cache[paper_id]
    m = META[paper_id]
    files = []
    pdf_name = Path(m.get("file", "") or "").stem
    stem = pdf_name or f"{m['file_author']} - {m['file_year']} - {m['file_title']}"
    if m.get("doi") and not m.get("chapter"):
        if _lib_by_doi is None:
            _lib_by_doi = {}
            for f in LIBRARY.glob("*/document.md"):
                head = f.read_text(encoding="utf-8", errors="ignore")[:4000]
                k = re.search(r"^doi:\s*[\"']?(10\.[^\s\"']+)", head, re.M | re.I)
                if k:
                    _lib_by_doi.setdefault(k.group(1).lower().rstrip("."), f)
        if m["doi"].lower() in _lib_by_doi:
            files.append(_lib_by_doi[m["doi"].lower()])
    for d in MD_DIRS:  # the library's conversion first: it is cleaner than the project's
        files += [f for f in d.glob("*.md") if f.stem == stem]
    out = []
    for f in files:
        text = _strip_markdown(f.read_text(encoding="utf-8", errors="ignore"))
        idx = [i for i, ch in enumerate(text) if ch.isalnum()]
        out.append((str(f), text, idx))
    _md_cache[paper_id] = out
    return out


def clean_sentence(paper_id: str, sentence: str) -> tuple[str, str]:
    """The same sentence from a Markdown version of the paper, if it matches exactly once spaces,
    punctuation and case are ignored; otherwise the PDF text unchanged. Returns (text, source)."""
    key = "".join(ch.lower() for ch in sentence if ch.isalnum())
    if len(key) < 30:
        return sentence, "pdf"
    for path, text, idx in _md_texts(paper_id):
        flat = "".join(text[i].lower() for i in idx)
        at = flat.find(key)
        if at < 0:
            continue
        start, end = idx[at], idx[at + len(key) - 1] + 1
        while end < len(text) and text[end] in ".!?)\"'’”]":  # keep the sentence's closing punctuation
            end += 1
        return text[start:end].strip(), "md"
    return sentence, "pdf"


_CORPUS: dict[str, int] | None = None


def _corpus() -> dict[str, int]:
    """Word counts across every passage of every paper: the dictionary for repairs."""
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = {}
        for f in {f.name: f for d in PASSAGE_DIRS for f in d.glob("*.jsonl")}.values():
            for line in open(f, encoding="utf-8"):
                txt = json.loads(line)["text"].translate({0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl"})
                for w in re.findall(r"[A-Za-z]+", txt):
                    w = w.lower()
                    _CORPUS[w] = _CORPUS.get(w, 0) + 1
    return _CORPUS


FUNCTION = set("""a an the of to in on for at by as be is it its or and but if so no not we he she they them
this that these those see out up off over into from with than then there here are was were has have had
do does did can may will would could should all any one two our your their his her who whom what when
where why how""".split())
_WORDLIST: set[str] | None = None


def _in_wordlist(w: str) -> bool:
    """The standard word list, allowing the usual endings (-s, -es, -ed, -ing, -ied, -ly)."""
    global _WORDLIST
    if _WORDLIST is None:
        _WORDLIST = {x.strip().lower() for x in open("/usr/share/dict/words", encoding="utf-8")}
    stems = {w}
    for end, add in (("ies", "y"), ("ied", "y"), ("es", ""), ("s", ""), ("ed", ""), ("ed", "e"), ("d", ""),
                     ("ing", ""), ("ing", "e"), ("ly", ""), ("al", "")):
        if w.endswith(end) and len(w) > len(end) + 2:
            stems.add(w[: -len(end)] + add)
    return any(x in _WORDLIST for x in stems)


def repair(sentence: str) -> str:
    """Join words the PDF text split apart, using the papers themselves as the dictionary.
    Two neighbouring pieces are joined only when the joined word occurs in the papers at least
    twice and one piece is a known split fragment: a hyphen gap ("discov - ery"), a ligature
    ("speci fi ed"), a stray single letter ("m anager"), or a piece that never occurs as a word
    on its own ("Pro cesses"). Real word pairs are left alone."""
    count = _corpus()
    lig = {"fi", "fl", "ff", "ffi", "ffl"}
    tokens = re.split(r"(\s+-\s+|\s+)", sentence)
    words, seps = tokens[0::2], tokens[1::2]
    changed = True
    while changed:
        changed = False
        for i in range(len(words) - 1):
            m1 = re.match(r"^(.*?)([A-Za-z]+)$", words[i])
            m2 = re.match(r"^([a-z]+)(.*)$", words[i + 1])
            if not (m1 and m2):
                continue
            left, right = m1.group(2), m2.group(1)
            joined = (left + right).lower()
            if count.get(joined, 0) < 2 and not _in_wordlist(joined):
                continue
            if left.lower() in FUNCTION or right in FUNCTION:
                continue  # never merge into a common word: "a lone", "see ms", "for mal" stay as printed
            cl, cr, cj = count.get(left.lower(), 0), count.get(right, 0), max(count.get(joined, 0), 1)
            rare = min(cl, cr) < 100 and min(cl, cr) * 5 < cj  # one piece rare beside the whole word
            fragment = (seps[i].strip() == "-" or right in lig or left.lower() in lig
                        or right.startswith(("fi", "fl", "ff")) or left.lower().endswith(("fi", "fl", "ff"))  # ligature splits
                        or (len(left) == 1 and left not in "aAI") or (len(right) == 1 and right not in "a")
                        or cl == 0 or cr == 0 or rare)
            if fragment:
                words[i] = words[i] + words[i + 1]
                del words[i + 1], seps[i]
                changed = True
                break
    return "".join(w + (seps[k] if k < len(seps) else "") for k, w in enumerate(words))


def cite(pid: str) -> dict:
    m = META[pid]
    fa = AUTHOR.get(pid, m["file_author"])
    year = YEAR.get(fa) or (m.get("year") if m.get("year") and abs(m["year"] - int(m["file_year"][:4])) <= 1 else int(m["file_year"][:4]))
    title = m.get("chapter") and f"{m['chapter']}. In {m['book']}" or m.get("title") or m["file_title"]
    venue = m.get("journal") or m.get("publisher") or ""
    return {"short": f"{fa.replace(' et al', ' et al.')} ({year})", "title": title, "venue": venue,
            "url": f"https://doi.org/{m['doi']}" if m.get("doi") else ""}


def main(out: str) -> None:
    draft = {c["id"]: c for c in json.loads(DRAFT.read_text(encoding="utf-8"))["codes"]}
    rows = list(csv.DictReader(open(REVIEW, encoding="utf-8")))
    groups = []
    for name, sq, asks in GROUPS:
        if name == "anomaly":
            codes = [{"id": c["id"], "label": c["label"], "definition": "",
                      "applies_when": c["applies_when"], "does_not_apply_when": c["does_not_apply_when"],
                      "sources": [], "also": [], "more": 0} for c in MISFIT["codes"]]
        else:
            codes = []
            for r in rows:
                if r["group"] != name or r["core"] != "yes":
                    continue
                d = draft[r["id"]]
                by_paper: dict[str, list[str]] = {}
                for pid in d["passage_ids"]:
                    by_paper.setdefault(pid.split(":")[0], []).append(pid)
                works: dict[str, dict] = {}  # one entry per work: book chapters collapse into the book
                for p in d["papers"]:
                    c = cite(p)
                    w = works.setdefault(c["short"] + c["url"], dict(c, pids=[]))
                    w["pids"] += by_paper.get(p, [])
                ranked = sorted(works.values(), key=lambda w: -len(w["pids"]))
                quoted = [dict({k: v for k, v in w.items() if k != "pids"}, quote=best_sentence(d, w["pids"]))
                          for w in ranked[:QUOTED]]
                listed = [{k: v for k, v in w.items() if k != "pids"} for w in ranked[QUOTED:]]
                codes.append({"order": ORDER.get(r["id"], 99), "id": r["id"], "label": r["label"], "definition": r["definition"],
                              "applies_when": r["applies_when"], "does_not_apply_when": r["does_not_apply_when"],
                              "sources": quoted, "also": listed, "more": 0})
        codes.sort(key=lambda c: c.get("order", 99))
        noncore = sum(1 for r in rows if r["group"] == name and r["core"] == "no")
        groups.append({"name": name, "sq": sq, "asks": asks, "codes": codes, "noncore": noncore})
    Path(out).write_text(json.dumps({"review": REVIEW.name, "groups": groups}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out, "from", REVIEW.name, sum(len(g["codes"]) for g in groups), "codes")


if __name__ == "__main__":
    main(sys.argv[1])
