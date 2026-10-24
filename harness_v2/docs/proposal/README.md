# Proposal (Organization Science special issue, Stage 1)

`build_proposal.js` writes `proposal.docx`: the 1,500-2,000 word proposal
due 1 November 2026. It uses the funnel figure from `../proposal_figures/`.
The technical appendix is `../technical_document.docx`.

```bash
node build_proposal.js ../proposal_figures/funnel.png proposal.docx
python ../source/readability_check.py proposal.docx
```

Edit the text in `build_proposal.js`, not in Word. Cite only sources held and
read in full.
