"""Find publication details and DOI links for the papers the draft codebook cites.

Usage: python metadata.py
Adds any missing paper to harness/codebook/paper_metadata.json; entries already
there are kept. Rules, in order:
  1. A DOI printed in the PDF's first pages, confirmed on Crossref by title.
  2. Otherwise a Crossref search, accepted only if the file's title words are
     contained in the Crossref title, the first author matches and the year is
     within two of the file name's year.
  3. Otherwise no link; the paper is cited by the details in its file name.
Only titles and author names are sent to Crossref.
"""
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

H = Path(__file__).resolve().parents[3] / "harness"
RUN = H / "runs" / "20261012-124904"
OUT = H / "codebook" / "paper_metadata.json"
UA = {"User-Agent": "harness-lookup/0.1 (mailto:vyassreenivas@gmail.com)"}


def norm(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", "", s).split()


def crossref(path: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request("https://api.crossref.org/" + path, headers=UA), timeout=30) as r:
        return json.load(r)["message"]


def details(it: dict) -> dict:
    return {"doi": it["DOI"].lower(), "title": " ".join((it.get("title") or [""]) + (it.get("subtitle") or [])),
            "journal": (it.get("container-title") or [""])[0],
            "year": (it.get("issued", {}).get("date-parts", [[None]])[0][0]),
            "volume": it.get("volume", ""), "issue": it.get("issue", ""), "page": it.get("page", ""),
            "authors": [(a.get("family") or a.get("name", "")) for a in it.get("author", [])]}


def title_ok(file_title: str, title: str) -> bool:
    ft = norm(file_title)
    return " ".join(ft[:min(len(ft), 6)]) in " ".join(norm(title))


def lookup(pid: str, file: str, run: Path = RUN) -> dict:
    name = Path(file).stem
    m = re.match(r"(.+?) - (\d{4})[a-z]? - (.+)", name)
    au, yr, ti = m.groups() if m else ("", "0", name)
    rec = {"paper_id": pid, "file_author": au, "file_year": yr, "file_title": ti}
    if au.startswith("Merton and Barber"):
        return dict(rec, book="The Travels and Adventures of Serendipity: A Study in Sociological Semantics and the Sociology of Science",
                    publisher="Princeton University Press", year=2004, authors=["Merton", "Barber"], chapter=ti,
                    doi="10.1515/9781400841523", doi_source="book DOI (chapters have none)")
    pages = json.loads((run / "pages" / f"{pid}.json").read_text(encoding="utf-8"))
    text = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in (pages if isinstance(pages, list) else pages.get("pages", []))[:3])
    found = re.search(r"(?:doi\.org/|doi:?\s*)(10\.\d{4,9}/[^\s\"<>]+)", text, re.I)
    if found:
        doi = found.group(1).rstrip(".,;)*").lower()
        try:
            it = crossref("works/" + urllib.parse.quote(doi))
            if title_ok(ti, " ".join((it.get("title") or [""]) + (it.get("subtitle") or []))):
                return dict(rec, **details(it), doi_source="pdf, confirmed on Crossref")
        except Exception:
            pass
    q = urllib.parse.urlencode({"query.bibliographic": f"{ti} {au}", "rows": 8,
                                "select": "DOI,title,subtitle,container-title,issued,author,volume,issue,page"})
    try:
        items = crossref("works?" + q)["items"]
    except Exception:
        items = []
    first = norm(au)[:1]
    for it in items:
        d = details(it)
        fam = any(norm(a)[:1] == first for a in d["authors"] if a)
        if fam and title_ok(ti, d["title"]) and d["year"] and abs(d["year"] - int(yr)) <= 2:
            return dict(rec, **d, doi_source="Crossref, title, author and year checked")
    return rec


def main() -> None:
    meta = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    inventory = {p["paper_id"]: p for p in json.loads((RUN / "inventory.json").read_text(encoding="utf-8"))}
    draft = json.loads((RUN / "codebook_draft.json").read_text(encoding="utf-8"))
    needed = sorted({p for c in draft["codes"] for p in c["papers"]} - set(meta))
    for pid in needed:
        meta[pid] = lookup(pid, inventory[pid]["file"])
        time.sleep(0.2)
    added = H / "codebook" / "added_papers.json"  # papers read after the draft
    if added.exists():
        a = json.loads(added.read_text(encoding="utf-8"))
        arun = H / "runs" / a["run"]
        ainv = {p["paper_id"]: p for p in json.loads((arun / "inventory.json").read_text(encoding="utf-8"))}
        later = sorted({x["candidate_id"].split(":")[0] for x in a["maps"] + a["new_codes"]} - set(meta))
        for pid in later:
            meta[pid] = lookup(pid, ainv[pid]["file"], arun)
            time.sleep(0.2)
        needed += later
    OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"added {len(needed)}; {sum('doi' in m for m in meta.values())} of {len(meta)} have a link")
    for pid in needed:
        if "doi" not in meta[pid]:
            print("  no link:", meta[pid]["file_author"], meta[pid]["file_year"], meta[pid]["file_title"][:60])


if __name__ == "__main__":
    main()
