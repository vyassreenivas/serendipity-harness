# Source of technical_document.docx

- `flow.py` draws `flow.png`, the harness as three boxes (build the codebook, code the interviews, analyse) with a loop until the codebook freezes (page 1). The funnel version is a proposal figure, in `../proposal_figures/`.
- `tree.py` draws `tree.png`, the Stage 1 overview: question, sub-questions, groups.
- `codebook_map.py` draws `codebook_map.png`, how the codebook is built: groups, all codes and core codes, with one group worked through (Stages 2 to 5 page).
- `build.js` writes `../technical_document.docx` from the text in the script
  and the three figures (needs the `docx` package for Node, version 9).

```bash
python flow.py flow.png
python tree.py tree.png
python codebook_map.py codebook_map.png
node build.js flow.png tree.png codebook_map.png ../technical_document.docx
```

Check readability after each edit:

```bash
python readability_check.py ../technical_document.docx
```

The text is in plain English: short sentences (a 30-word ceiling), the active
voice where it reads naturally, and one definition for each key term (defined where first used).

Layout: page 1 is the whole flow. Each built stage gets exactly one page in
the same template (what it does; in and out; who does the work; one figure;
a steps table with the general rule beside what it gave for serendipity; how
it can fail; state). Each stage page is followed by one details page (key tables,
rules, open points, sources). There is no appendix: the full record is in the
repository's stage folders.

Edit the text in `build.js`, not in Word, or the next build overwrites the
edit. Add a section here each time a stage is built, and mark it built in
`flow.py` (the `BUILT` set).
