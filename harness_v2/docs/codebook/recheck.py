"""Re-check code-paper links that no cited sentence confirmed, against the whole paper.

Usage: python recheck.py codebook_review.xlsx SHORTLIST.json [--per-pair 8]

The check that confirms each link reads only the passages the model cited. When
none of them states the code, this step looks at the whole paper: it scores every
sentence in the paper against the code's wording (the same fixed rule as
best_sentence) and writes the closest sentences, numbered, to SHORTLIST.json.
A reader (a model with prompt 4 in drafts/prompt_draft2.md, or a researcher) then
decides for each link whether one of those sentences states the code, and the
outcome of every link goes into harness/codebook/recheck.json. The shortlist holds
paper text: write it outside the repository (for example harness_v2/outputs/).
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter

from export import BOILER, passage, sentences, tidy, words
from workbook import NONE, cite, load_draft, state_from_workbook


def paper_sentences(paper: str) -> list[tuple[str, int, str]]:
    """Every sentence of a paper as (passage id, sentence number, text), in order."""
    passage("%s:p001:01" % paper)  # loads the paper's passages
    from export import _passages
    out = []
    for pid, rec in sorted(_passages.get(paper, {}).items()):
        for k, s in enumerate(sentences(rec["text"]), 1):
            out.append((pid, k, s))
    return out


def shortlist(code: dict, papers: list[str], n: int) -> list[dict]:
    target = Counter(words(" ".join([code["label"], code["definition"], code["applies_when"]])))
    scored = []
    for paper in papers:
        for pid, k, sent in paper_sentences(paper):
            sent = tidy(sent)
            if sent is None or not 8 <= len(sent.split()) <= 60 or BOILER.search(sent):
                continue
            ws = set(words(sent))
            score = sum(1 + math.log(target[w]) for w in ws if w in target) / math.sqrt(len(ws) or 1)
            scored.append((score, pid, k, sent))
    scored.sort(key=lambda x: -x[0])
    return [{"sentence_id": f"{pid}:s{k}", "pdf_page": int(re.search(r":p(\d+):", pid).group(1)), "text": sent}
            for _, pid, k, sent in scored[:n]]


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("xlsx"); a.add_argument("out"); a.add_argument("--per-pair", type=int, default=8)
    x = a.parse_args()
    state, draft = state_from_workbook(x.xlsx), load_draft()
    pairs = []
    for cid, works in NONE.items():
        if state.get(cid, {}).get("Status") != "core":
            continue
        code = draft[cid]
        for work in works:
            papers = [p for p in code["papers"] if cite(p)["short"] + cite(p)["url"] == work]
            pairs.append({"code": cid, "label": state[cid]["Label"], "code_it_when": state[cid]["Code it when"],
                          "definition": code["definition"], "work": cite(papers[0])["short"] if papers else work,
                          "papers": papers, "sentences": shortlist(code, papers, x.per_pair)})
    json.dump({"pairs": pairs}, open(x.out, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {x.out}: {len(pairs)} links, {sum(len(p['sentences']) for p in pairs)} sentences")


if __name__ == "__main__":
    main()
