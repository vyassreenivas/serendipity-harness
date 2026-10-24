const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, LevelFormat, Footer, PageNumber, PageBreak,
  TableOfContents,
} = require("docx");

const [, , FLOW, TREE, MAP, OUT] = process.argv;
const FONT = "Calibri";
const TW = 9360; // text width, US Letter with 1-inch margins

// **bold** and *italic* inside a string
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: 19, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 120 }, ...o });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: false });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(t), spacing: { after: 60 } });
const N = (t, ref = "steps") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60 } });
const Label = (label, t) => new Paragraph({ children: [new TextRun({ text: label + " ", bold: true }), ...runs(t)], spacing: { after: 100 } });

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(header, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, head) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: head ? { fill: "1F3A5F", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: String(t).split("\n").map((line) => new Paragraph({
      children: runs(line, head ? { bold: true, color: "FFFFFF", size: 19 } : { size: 19 }),
    })),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, widths[i], false)) }))],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 60 } });
const Caption = (t) => new Paragraph({ children: runs(t, { italics: true, size: 19, color: "555555" }), spacing: { before: 60, after: 200 } });

// One stage, in the same five parts every time
function stage(title, s) {
  return [H3(title),
    Label("What it does.", s.does),
    Label("In and out.", s.io),
    Label("Who does the work.", s.who),
    ...(Array.isArray(s.why) ? [Label("Why this design.", ""), ...s.why.map((x) => B(x))] : [Label("Why this design.", s.why)]),
    ...(Array.isArray(s.fail) ? [Label("How it can fail.", ""), ...s.fail.map((x) => B(x))] : [Label("How it can fail.", s.fail)]),
    Label("State on 14 October 2026.", s.state)];
}

const flowImg = fs.readFileSync(FLOW);
const FLOW_H = Math.round(600 * flowImg.readUInt32BE(20) / flowImg.readUInt32BE(16));
const treeImg = fs.readFileSync(TREE);
const mapImg = fs.readFileSync(MAP);
const MAP_H = Math.round(600 * mapImg.readUInt32BE(20) / mapImg.readUInt32BE(16));
const TREE_H = Math.round(490 * treeImg.readUInt32BE(20) / treeImg.readUInt32BE(16));
const Note = (t) => new Paragraph({ children: [new TextRun({ text: "Note: ", bold: true }), ...runs(t)], indent: { left: 360 }, spacing: { before: 60, after: 120 } });
const children = [
  // ---------- Page 1: the flow ----------
  new Paragraph({ children: [new TextRun({ text: "A literature-to-coding harness for qualitative research", bold: true, size: 36, color: "1F3A5F" })], spacing: { after: 80 } }),
  new Paragraph({ children: [new TextRun({ text: "Technical appendix to the proposal for the Organization Science special issue. Vyas Sreenivas and Ravi S. Kudesia. Draft, 23 October 2026.", size: 20, color: "555555" })], spacing: { after: 200 } }),
  P("Qualitative research has two broad modes. In the first, researchers collect their own data and build theory inductively, refining their questions as they go. In the second, a large body of text already exists, such as thousands of published founder interviews, and researchers bring concepts from the literature to it."),
  P("The harness serves the second mode. It applies existing theory to large archival text and keeps what the theory does not explain as anomalies to theorize from, which makes the approach abductive (Timmermans and Tavory 2012). It works in three boxes (Figure 1). We make the judgments, a model reads and codes at scale, and fixed code checks every output. Our worked example is serendipity in founder interviews from Starter Story."),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: flowImg, transformation: { width: 600, height: FLOW_H }, altText: { title: "The harness in three boxes", description: "Box 1, build the codebook (Stages 1 to 5): papers and the research question in; the model drafts codes and we review and freeze them; a frozen codebook out. Box 2, code the interviews (Stages 6 to 8): the codebook and interviews in; the model codes, we code a sample and compare; coded interviews out. A dotted loop from box 2 to box 1: revise until the codebook freezes. Box 3, analyse: coded interviews in; counts and patterns by script, and we interpret and build theory; findings out.", name: "flow" } })] }),
  Caption("Figure 1. The harness. Each step is coloured by who does it. In box 1 we review the model's draft until the codebook freezes. In box 2 we compare our coding with the model's, batch by batch, and changes go back to the codebook."),

  // ---------- Stage 1 ----------
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Stage 1. Choose the literature and break down the question")], pageBreakBefore: true }),
  P("We start by reading the literature closely and choosing the works whose views are worth integrating. We then name what kind of question we are asking. We then split it into sub-questions and turn each sub-question into analysis groups: the questions a coder asks of the data. An anomaly group holds whatever no other group asks about. Figure 2a shows the method for any study, and Figure 2b shows it for serendipity."),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60 }, children: [new ImageRun({ type: "png", data: treeImg, transformation: { width: 490, height: TREE_H }, altText: { title: "Stage 1", description: "a: a research question splits into sub-questions, each giving analysis groups, plus an anomaly group. b: the serendipity question, its six sub-questions and eleven analysis groups.", name: "tree" } })] }),
  Caption("Figure 2. Stage 1. (a) The method for any study. (b) Applied to serendipity: one research question, six sub-questions and eleven analysis groups."),
  table(["Step", "What we do"], [
    ["1 Choose the literature", "Read the literature closely; choose the seminal works whose views differ and are worth integrating, and the assumptions worth questioning."],
    ["2 Name the kind of question", "Decide whether it asks how something happens (process), what explains differences (variance) or what something is (conceptual)."],
    ["3 Split it into parts", "List the topic, the action, the time span, the people, the place and the data."],
    ["4 Write sub-questions", "Write the standard sub-questions for that kind of question, in the study's own terms."],
    ["5 Trace and test each one", "Keep a sub-question only if it comes from the main question, the data can answer it and it repeats no other."],
    ["6 Write the analysis groups", "Turn each sub-question into the questions asked of every part of the data, and add an anomaly group."],
    ["7 Choose the data", "Choose an archival source whose texts can answer the sub-questions."],
  ], [2600, 6760]),
  Caption("Table 1. The steps of Stage 1, following Sandberg and Alvesson (2011), Maxwell (2009), Podsakoff et al. (2016) and Staller (2022)."),

  // ---------- Stages 2 to 5: the codebook ----------
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Stages 2 to 4. Build the codebook")], pageBreakBefore: true }),
  P("The codebook has three levels. The groups come from Stage 1. The codes come from the literature. The core codes are the ones coders apply. A model builds the draft in three steps, shown in Figure 3, and we then review it (Stage 5). One page, the codebook trail, shows every step with its evidence."),
  N("**Read the papers.** A model reads each paper on its own, with the same fixed prompt. For each idea it proposes a candidate code, places it in one group and cites the passages that state it. Fixed code checks every cited passage against the paper. From 113 papers this gave 1,893 candidate codes.", "s1"),
  N("**Merge the candidates.** Within each group, the model merges candidates that state the same idea into one drafted code. Each drafted code keeps every paper and passage behind it. Off-topic candidates are set aside with a reason. This gave 369 drafted codes.", "s1"),
  N("**Suggest the core codes.** The model suggests a status for each drafted code (core, reference or reject) and plain wording for the core codes. For each core code and each paper behind it, it reads the cited passages and picks the sentence that states the code, with its page. Where no sentence does, it says so. These are suggestions for our review.", "s1"),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60 }, children: [new ImageRun({ type: "png", data: mapImg, transformation: { width: 600, height: MAP_H }, altText: { title: "How the codebook is built", description: "113 papers give 1,893 candidate codes, merged into 369 drafted codes sorted into the Stage 1 groups. 45 are marked core, 314 reference and 10 reject. Then 10 anomaly codes are added, one per group, and coders apply 55 codes in 11 groups. Below, the trigger group: six core codes, 21 reference codes and one anomaly code.", name: "codebook_map" } })] }),
  Caption("Figure 3. How the codebook is built for serendipity. Top: papers become candidate codes, then drafted codes in the Stage 1 groups, which we mark core, reference or reject; anomaly codes come last. Bottom: one group. Colours as in Figure 1."),
  P("Every code sits in one group. Core and reference codes come from the same draft and differ only in status, so a reference code can become core if the interviews call for it."),
  P("**The evidence rule.** A code stays only if a paper states it in a sentence. A paper stays with a code only if one of its sentences states that code. For serendipity, 65 of the 473 pairs of core code and paper had no such sentence and were dropped. Every core code kept at least one sentence, and 74 papers remain behind the core codes."),
  P("**Definitions.** Some papers define serendipity as a combination of parts. We keep each such definition as a rule over the core codes, not as a code. Coders tick only the parts, and the coding page shows which definitions an episode meets. Each rule carries the papers' own sentences."),
  B("**Busch (2024):** agency, surprise and value. Met when Agency, Surprise and Value are all coded; six papers state it."),
  B("**Dew (2009):** search, chance and prior knowledge. Met when Already searching, Surprise and Relevant expertise are all coded; six papers state it."),
  B("**Walpole, after Merton and Barber (2004):** accident and sagacity. Met when Surprise and Connecting the dots are both coded; seven works state it."),
  P("Comparing the episodes that meet each definition is itself a result: it shows how much the choice of definition changes what counts as serendipity."),
  new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("The codebook trail")], pageBreakBefore: true }),
  P("The codebook trail (codebook_trail.html) lets a reader follow the build without the workbook. It is one page with three views."),
  B("**By sub-question.** Each sub-question opens into its groups, core codes and, under the first, the definitions. Each code or definition opens into the paper sentences that state it, with page and link. Every level shows how many candidate codes became drafted and core codes."),
  B("**By paper.** Each paper shows what it says under each sub-question, and which code each sentence supports."),
  B("**When no code fits.** The anomaly codes, which have no paper evidence by design."),
  P("Table 2 sums up the trail for each group."),
  // From codebook_review.xlsx (Evidence sheet, core codes), 23 October 2026.
  table(["Group", "Question asked of each episode", "Candidate → drafted → core", "Papers", "Most used sources"], [
    ["Definition", "Does this episode count as serendipity?", "130 → 21 → 4", "22", "Balzano (2022); Busch (2024); Fultz and Hmieleski (2025); Merton and Barber (2004)"],
    ["Type", "What kind of serendipity is it?", "104 → 37 → 6", "17", "Yaqub (2018); Mirvahedi and Morrish (2017); Fultz and Hmieleski (2025); Busch and Grimes (2023)"],
    ["Rival", "What else could explain the same story?", "174 → 32 → 4", "38", "Busch (2024); Kirzner (1997); Mirvahedi and Morrish (2017); Balzano (2022)"],
    ["Trigger", "What unexpected event started it?", "160 → 27 → 6", "42", "Andel (1994); Copeland et al. (2023); Balzano (2022); Merton and Barber (2004)"],
    ["Background", "What did the founder already have?", "173 → 34 → 4", "28", "Copeland et al. (2023); Reijonen and Heroum (2026); Andel (1994); Cunha et al. (2010)"],
    ["Mechanism", "What did the founder do to turn it into something?", "278 → 50 → 5", "39", "Merton and Barber (2004); Busch (2024); Copeland et al. (2023); Busch and Grimes (2023)"],
    ["Role", "What part did it play in the venture?", "109 → 22 → 4", "30", "Dew (2009); Balzano (2022); Copeland et al. (2023); Mirvahedi and Morrish (2017)"],
    ["Outcome", "What came of it?", "144 → 39 → 4", "26", "Busch (2024); Cunha et al. (2010); Balzano (2022); Smith and Hilbolling (2025)"],
    ["Condition", "What made it easier or harder?", "379 → 72 → 4", "27", "Copeland et al. (2023); Merton and Barber (2004); Sarasvathy (2001); Balzano (2022)"],
    ["Account", "How does the founder tell it afterwards?", "150 → 35 → 4", "32", "Oo et al. (2025); Merton and Barber (2004); Busch and Grimes (2023); Mirvahedi and Morrish (2017)"],
  ], [1250, 2500, 1500, 800, 3310]),
  Caption("Table 2. The literature behind each group. Papers counts those that state at least one core code (74 in all). Of the 1,893 candidates, 1,801 were merged; the rest were set aside."),

  // ---------- Stage 5: review ----------
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Stage 5. Review and freeze the codebook")], pageBreakBefore: true }),
  P("The model's draft is a proposal. We review every code together, in a workbook that shows each code with its evidence, and settle any disagreement before a code is final."),
  B("**Check that codes and quotes fit, both ways.** Each code's name and wording should match its quoted sentences, and each sentence should state its code. Drop a paper from a code where no sentence does, and a code that no paper states."),
  B("**Check each code against its literature.** A code must represent the papers it comes from faithfully. Correct any code that misreads them."),
  B("**Check the merge.** Each code should hold one idea. Split a code that holds two, and reject a duplicate by naming the code it repeats."),
  B("**Set the status.** Mark each code core, reference or reject. Keep about four core codes per group, so that a coder holds 30 to 40 codes at once."),
  B("**Reword the core codes** in founders' terms. Each gets a label of up to 5 words and when to code it in up to 20. It also gets a made-up example and its nearest look-alike in up to 15."),
  B("**Record a reason** for every rejection and every change to the model's wording."),
  B("**Write the anomaly codes,** one per group, once the core codes are set (next section)."),
  B("**Freeze.** Fixed code checks that every code has a decision, and a reason where one is needed. It then numbers the version and commits it. Any later change makes a new version."),
  P("For serendipity, the review gave 45 core, 314 reference and 10 rejected codes."),

  // ---------- Anomaly codes ----------
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Anomaly codes")], pageBreakBefore: true }),
  P("The core codes are deductive: they come from the literature. An interview can hold something the literature does not name, and the anomaly codes hold it. Each group has one anomaly code for what its core codes miss, and ANO-NEW takes what no group asks about. Starting from theory and letting surprising data revise it makes the coding abductive (Timmermans and Tavory 2012). Anomalies are therefore a source of theory, not noise. When one recurs, we search for papers that explain it. If one does, it joins the codebook; if none does, the anomaly may mark a gap in the literature."),
  table(["Code", "Use it when", "Do not use it when"], [
    ["ANO-TYP", "The episode is serendipity, but no type code describes it", "A type fits roughly: use it and note the doubt"],
    ["ANO-RIV", "The account fits another explanation that is not a rival code", "The founder only denies chance: that is account"],
    ["ANO-TRG", "Something unexpected started it, but no trigger code names that kind of event", "The trigger is unclear: leave trigger blank"],
    ["ANO-BKG", "The founder brought something relevant that no background code covers", "It is a circumstance, not something the founder had: that is condition"],
    ["ANO-MEC", "The founder did something with the event that no mechanism code covers", ""],
    ["ANO-ROL", "It played a part in the venture other than starting, redirecting or advancing it", ""],
    ["ANO-OUT", "A result that no outcome code covers", ""],
    ["ANO-CND", "A circumstance that made it easier or harder, not covered by a condition code", ""],
    ["ANO-ACC", "A way of telling it that no account code covers", ""],
    ["ANO-NEW", "Relevant to the research question, but no group asks about it; for example, a co-founder rather than the founder saw the opportunity", "It belongs to a group: use that group's anomaly code"],
  ], [1300, 4560, 3500]),
  Caption("Table 3. Anomaly codes. An anomaly code that is used often shows that its group needs revision."),
  N("**Capture every anomaly** during coding, with a short label, the passages it rests on, and why no code fits (MacQueen et al. 1998).", "s2"),
  N("**Analyse the anomalies after each calibration round.** An anomaly becomes a code when it recurs or when we can give a theoretical reason (Carroll et al. 2013).", "s2"),
  N("**Analyse the anomaly pool** once the corpus is coded. The corpus is not recoded.", "s2"),

  // ---------- Stages 6 to 8 ----------
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Stages 6 to 8. Calibrate, then code the corpus")], pageBreakBefore: true }),
  P("We calibrate the codebook on interviews before the model codes the corpus. The prototype has run parts of each stage (Table 4)."),
  N("**Calibrate in rounds of 25 to 50 interviews** (MacQueen et al. 1998). Each round counts new codes and changes to what a code means. We freeze after the first round with neither, once agreement holds (Eisenhardt 1989; Guest et al. 2006; Hennink et al. 2017). About 150 interviews is a budget limit, not a target.", "s3"),
  N("**Test on 30 to 50 held-out interviews,** then let the model code the rest, with spot checks of about 5%.", "s3"),
  table(["Stage", "What it does", "Who does the work", "Run in the prototype"], [
    ["6 Calibration rounds", "We and the model code 25 to 50 interviews on the same worksheet", "Researchers and model", "Three models coded 5 interviews"],
    ["7 Compare and revise", "Measure agreement, analyse anomalies, revise the codebook", "Fixed code; researchers", "Comparison built and tested"],
    ["8 Held-out test and scale-up", "Test on unseen interviews; the model codes the rest with spot checks; we analyse the anomaly pool", "Researchers and model", "Not started"],
  ], [1900, 3460, 1900, 2100]),
  Caption("Table 4. Stages 6 to 8."),
  H2("Data, models and reproducibility"),
  B("**Data and rights.** Papers and the 1,972 Starter Story interviews are not in the repository. Interview text goes only to a model the run setup names, and fictional counterparts let examples be published."),
  B("**Models and records.** Each run names its models and their versions, and keeps every input fingerprint, model call and check."),
  B("**Open models.** The prototype runs on Claude. The harness also runs open models on a researcher's own computer, so no paid model or software is required. An open-source release follows."),

  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("References")], pageBreakBefore: true }),
  ...[
    "Maxwell, J. A. (2009). Designing a qualitative study. In L. Bickman and D. J. Rog (Eds.), *The SAGE Handbook of Applied Social Research Methods* (2nd ed., pp. 214–253). Sage.",
    "Podsakoff, P. M., MacKenzie, S. B., and Podsakoff, N. P. (2016). Recommendations for creating better concept definitions in the organizational, behavioral, and social sciences. *Organizational Research Methods*, 19(2), 159–203.",
    "Sandberg, J., and Alvesson, M. (2011). Ways of constructing research questions: Gap-spotting or problematization? *Organization*, 18(1), 23–44. doi:10.1177/1350508410372151.",
    "Staller, K. M. (2022). Confusing questions in qualitative inquiry: Research, interview, and analysis. *Qualitative Social Work*, 21(2), 227–234.",
    "Eisenhardt, K. M. (1989). Building theories from case study research. *Academy of Management Review*, 14(4), 532–550. doi:10.5465/amr.1989.4308385.",
    "Guest, G., Bunce, A., and Johnson, L. (2006). How many interviews are enough? An experiment with data saturation and variability. *Field Methods*, 18(1), 59–82.",
    "Hennink, M. M., Kaiser, B. N., and Marconi, V. C. (2017). Code saturation versus meaning saturation: How many interviews are enough? *Qualitative Health Research*, 27(4), 591–608.",
    "Timmermans, S., and Tavory, I. (2012). Theory construction in qualitative research: From grounded theory to abductive analysis. *Sociological Theory*. doi:10.1177/0735275112457914.",
    "Vila-Henninger, L., et al. (2024). Abductive coding: Theory building and qualitative (re)analysis. *Sociological Methods & Research*, 53(2), 968–1001.",
    "Carroll, C., Booth, A., Leaviss, J., and Rick, J. (2013). \"Best fit\" framework synthesis: Refining the method. *BMC Medical Research Methodology*, 13, 37.",
    "MacQueen, K. M., McLellan, E., Kay, K., and Milstein, B. (1998). Codebook development for team-based qualitative analysis. *Cultural Anthropology Methods*, 10(2), 31–36.",
  ].sort((x, y) => x.localeCompare(y)).map((r) => new Paragraph({ children: runs(r), indent: { left: 360, hanging: 360 }, spacing: { after: 80 } })),
];

const numbering = { config: [
  { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
  ...["steps", "lit", "open", "s1", "s2", "s3", "s4", "s5", "s6"].map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] })),
] };

const doc = new Document({
  creator: "Vyas Sreenivas", title: "A literature-to-coding harness: technical document, version 2",
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, color: "1F3A5F", font: FONT }, paragraph: { spacing: { before: 360, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true, color: "1F3A5F", font: FONT }, paragraph: { spacing: { before: 260, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, color: "333333", font: FONT }, paragraph: { spacing: { before: 220, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering,
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["Technical appendix, working draft, 17 October 2026  ·  ", PageNumber.CURRENT], size: 17, color: "777777" })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
