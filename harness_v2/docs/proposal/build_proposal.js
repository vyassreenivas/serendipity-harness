// Writes the Stage 1 proposal for the Organization Science special issue.
// Usage: node build_proposal.js ../proposal_figures/funnel.png proposal.docx   (needs docx@9)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, LevelFormat, Footer, PageNumber,
} = require("docx");

const [, , FUNNEL, OUT] = process.argv;
const FONT = "Calibri";

function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (t) => new Paragraph({ children: runs(t), spacing: { after: 120 } });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const B = (t) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(t), spacing: { after: 60 } });
const N = (t) => new Paragraph({ numbering: { reference: "steps", level: 0 }, children: runs(t), spacing: { after: 60 } });
const Caption = (t) => new Paragraph({ children: runs(t, { italics: true, size: 19, color: "555555" }), spacing: { before: 60, after: 200 } });
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(header, rows, widths) {
  const cell = (t, w, head) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: head ? { fill: "1F3A5F", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: runs(t, head ? { bold: true, color: "FFFFFF", size: 19 } : { size: 19 }) })],
  });
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, widths[i], false)) }))],
  });
}

const funnel = fs.readFileSync(FUNNEL);
const FH = Math.round(560 * funnel.readUInt32BE(20) / funnel.readUInt32BE(16));

const children = [
  new Paragraph({ children: [new TextRun({ text: "Theory at scale, judgment at the margins: an auditable harness for abductive coding with people and AI", bold: true, size: 32, color: "1F3A5F" })], spacing: { after: 80 } }),
  new Paragraph({ children: [new TextRun({ text: "Proposal for the Organization Science special issue \"AI-Assisted Frontiers in Organizational Science\". Vyas Sreenivas and Ravi S. Kudesia. Draft, 23 October 2026.", size: 20, color: "555555" })], spacing: { after: 200 } }),

  H1("1. The idea"),
  P("Qualitative research builds theory in two broad modes. In the first, researchers collect their own data, through fieldwork and interviews, and build theory as they go. In the second, a large body of text already exists, and researchers bring concepts from the literature to it. Archives of the second kind are growing fast. Ours holds 1,972 founder interviews published by Starter Story, far more than any team can read closely."),
  P("Because the second mode starts from theory, its core move is deductive coding: applying codes drawn from the literature to text (Hsieh and Shannon 2005; Robinson and Bailey-Rodriguez 2026). On its own, this move has two known weaknesses. Coders tend to find support for the theory they bring and to miss what it does not name (Hsieh and Shannon 2005). And labelling data with a prior framework adds little to theory; Langley calls it \"a mapping exercise\" (Gehman et al. 2018). In her account, existing theory takes a study part of the way, and what remains is the contribution."),
  P("Large language models (LLMs) make deductive coding cheap. Most work on using them in management research treats the model as a faster coder, checked against human labels. Carlson and Burbano (2026) show that reasonable choices of prompt and model can change a study's conclusions. Used this way, a model scales the mapping exercise, not the theorizing."),
  P("We propose a different division of labour: **the AI applies theory, and people theorize from what theory cannot hold.** A model codes the whole corpus with a codebook built from the literature. Every passage that matters to the question but fits no code is kept as an *anomaly*. People then analyse the anomalies abductively, treating surprises as the occasion for new theory (Timmermans and Tavory 2012; Vila-Henninger et al. 2024)."),
  P("This division follows how abduction works. Sætre and Van de Ven (2021) describe four steps: observe an anomaly, confirm it, generate hunches that might explain it, and evaluate them. The model does the first step across every interview. The corpus does the second, by showing whether an anomaly recurs or is a one-off (Cohen et al. 2025). The third and fourth steps stay with people, working together, as Sætre and Van de Ven recommend."),
  P("Scale is what makes the second step possible. A pattern in 2% of accounts may appear once, or not at all, in 20 hand-coded interviews. Across 1,972 it appears about 40 times, enough to compare cases and judge whether it is new theory or noise. The result is not faster coding. It is a kind of study that was not possible before: theory applied to a whole corpus, with judgment spent where theory runs out (Figure 1)."),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: funnel, transformation: { width: 560, height: FH }, altText: { title: "The harness as a funnel", description: "Part A builds the codebook from the question and the papers. Part B: the model codes the whole corpus with the frozen codebook; a calibration loop and held-out test sit beside it; people analyse the anomaly pool abductively", name: "funnel" } })] }),
  Caption("Figure 1. The harness. Part A builds the codebook. In Part B, we and the model calibrate the codebook on small rounds and test it on held-out interviews. The model then codes every interview deductively, and we analyse the anomaly pool abductively."),

  H1("2. The harness"),
  P("The harness runs in three boxes: build the codebook, code the interviews, and analyse. Each step is done by researchers, by a model, or by fixed code (an ordinary program), and the record shows which. Five principles run through it:"),
  B("**Researchers decide; the model proposes.** Nothing enters the codebook without a recorded human decision."),
  B("**The model points; the harness copies.** Models cite numbered passages and never type a quotation, so they cannot invent evidence."),
  B("**Fixed code checks every model output.** An identifier that does not exist is removed and logged, never silently repaired."),
  B("**People and the model code the same worksheet,** an open web page that saves to a plain file, so they can be compared on equal terms."),
  B("**Every decision is recorded and dated,** so a reader can see that the codebook was fixed before the coding it was tested on."),
  P("**Build the codebook.** We choose the literature and break the research question into sub-questions and analysis groups. Choosing the literature includes asking which of its assumptions are worth questioning (Sandberg and Alvesson 2011). A model reads each chosen paper for candidate codes, each tied to the passages it rests on, and merges them into a draft. We then review the draft. Each code must fit both its quotes and its literature. Each core code gets a definition, an example and an exclusion, the usual parts of a codebook entry (MacQueen et al. 1998; Roberts et al. 2019)."),
  P("**Anomaly codes** are the core of the design. Each analysis group has one for what its codes miss, and one more takes what no group asks about. Each anomaly records a short label, the passages it rests on, and why no code fits. Deductive coders are advised to look for evidence that contradicts, refines or expands a theory, not only evidence that supports it (Robinson and Bailey-Rodriguez 2026). Anomaly codes turn that advice into a required field. Text that no code fits is set aside and analysed later for new categories (Hsieh and Shannon 2005; Carroll et al. 2013). An anomaly becomes a code only by recurrence or by a written theoretical reason."),
  P("**Code the interviews.** We and the model code rounds of 25 to 50 interviews on the same worksheet, revising the codebook between rounds (MacQueen et al. 1998). Each round records new codes and changes to what a code means. The codebook freezes after the first round with neither, once agreement holds (Eisenhardt 1989; Guest et al. 2006; Hennink et al. 2017). We then test it on 30 to 50 held-out interviews. The model codes the rest, and we spot-check about 5%."),
  P("**Analyse.** Fixed code counts codes and patterns across the corpus. We study the anomaly pool, confirm which anomalies recur, and develop and weigh explanations for them together."),

  H1("3. First application: serendipity in entrepreneurship"),
  P("We test the harness on a hard case. Serendipity is contested: scholars disagree on what counts (Dew 2009; Busch 2024). It is rare, scattered through long accounts, and told after the fact, often tidied into a plan. A harness that can handle serendipity should handle easier constructs."),
  P("Our question is: *How does serendipity shape the entrepreneurial process, from the first idea to the developing venture?* We break it into six sub-questions, from what counts as serendipity to how founders tell it, and eleven analysis groups, one of them for anomalies. Busch's (2024) three conditions, agency, surprise and value, anchor the definition."),
  P("A whole corpus lets us ask what small samples cannot. We can test whether serendipity clusters early in a venture, as Mirvahedi and Morrish (2017) found in a small set of cases. We can compare a broad definition (Busch's three conditions) with a narrow one that requires the founder to be searching already (Dew 2009). The gap between them is itself a finding. And because the interviews are success stories told to a publishing platform, we code how founders tell serendipity as well as what happened. Brownell et al. (2024) did this for luck in 70 founder interviews; we can do it for 1,972."),

  H1("4. What we have done"),
  B("**A codebook drafted from the literature.** A model read 113 papers and book chapters and proposed 1,893 candidate codes, merged into a 369-code draft. The current draft gives coders 45 core codes and 10 anomaly codes; the other codes stay as reference."),
  B("**Evidence chosen by reading.** For every core code, we chose by reading the sentence in each paper that states it. Where no sentence does, the record says so rather than quoting off-topic text."),
  B("**A coding page.** Coders work on one open web page per interview, and it saves one row per episode to a plain file any analysis tool can read. A model has coded one interview on it as a pilot."),
  B("**A first comparison of models.** Three models coded 5 interviews. Claude Opus found 8 episodes tied to specific paragraphs; two small local models completed the task but read poorly. All three passed every format check, which shows why format checks need human comparison."),
  B("**A way to publish examples.** One model outlines a real interview; a second writes a fictional one from the outline alone, and fixed code measures what wording survives. A trial on 5 interviews kept shared five-word runs to 0.5 to 1.8%."),
  P("The submitted repository holds the code, every prompt, the run logs and instructions to run it. Papers and interviews are not in it, for copyright reasons. The technical appendix describes each stage and what the prototype has run."),

  H1("5. What we will do"),
  N("Review and freeze the codebook together."),
  N("Run calibration rounds with both of us and the model, then draw the held-out sample by a recorded seed."),
  N("Compare a commercial model with open models on the held-out sample: agreement with each of us, agreement with itself across runs, and cost."),
  N("Code the full corpus, analyse the anomaly pool, and report what it adds to theory on serendipity."),
  N("Release the harness so other researchers can run it with their own papers, question and corpus."),
  P("Steps 1 and 2 are planned before the January decision, so the development period can focus on the held-out test, the model comparison and the anomaly analysis. Each step ends with a frozen, recorded output that the next step reads. Partial progress therefore still yields a usable result: a codebook, an agreement report, or a model comparison."),

  H1("6. Key risks"),
  table(["Risk", "What we will do"], [
    ["The interviews are proprietary and cannot be shared", "Seek Starter Story's permission to share a subset; release fictional counterparts; publish interview identifiers, code and every model output that holds no interview text. Reproducing the method will not need the interviews"],
    ["Conclusions depend on the prompt or the model (Carlson and Burbano 2026)", "Repeat every coding run, use at least two models, and report every configuration tried, not only the best"],
    ["Deductive coding finds what it looks for (Hsieh and Shannon 2005)", "An anomaly code in every group; we code each interview before seeing the model's coding"],
    ["The model misses anomalies, hiding what the codebook cannot hold", "Spot checks count anomalies that people find and the model did not"],
    ["Agreement falls as the number of codes grows (Roberts et al. 2019)", "Coders apply only the core codes; the rest stay as reference"],
    ["The codebook is tuned to the interviews it was revised on", "A held-out sample, drawn by seed and unseen during development"],
    ["The codebook never settles", "A budget of about 150 calibration interviews; anomalies that keep appearing are reported as findings, not forced into codes"],
    ["Hosted models are retired", "Record each model's exact version; test open models so the harness does not depend on one vendor"],
  ], [3300, 6060]),
  gapP(),

  H1("7. If it works"),
  P("Qualitative researchers could apply theory to entire corpora without giving up close reading. The AI would do the reading the theory already explains, and people would do the reading it cannot. The anomaly pool would become a systematic and auditable source of new theory, rather than whatever a coder happened to notice."),
  P("The design also meets the call's criteria. It is auditable, because every model call, check and human decision is recorded. It is reproducible in method, because the prompts, code and seeds are released. It scales, because the costly human work grows with the anomalies rather than with the corpus. And it can be adopted, because it runs on open models and needs no paid software."),
  P("Because the harness takes papers, a question and a corpus as inputs, another team could run it on a different topic. And because every step is recorded, a reader could trace any finding back to the question, the papers and the passages it rests on."),

  H1("References"),
  ...[
    "Brownell, K. M., Cardon, M. S., Bolinger, M. T., and Covin, J. G. (2024). Choice or chance: How successful entrepreneurs talk about luck. *Journal of Small Business Management*, 62(3), 1684–1717.",
    "Busch, C. (2024). Towards a theory of serendipity: A systematic review and conceptualization. *Journal of Management Studies*. doi:10.1111/joms.12890.",
    "Carlson, N. A., and Burbano, V. (2026). The use of LLMs to annotate data in management research: Foundational guidelines and warnings. *Strategic Management Journal*, 47(3), 699–725. doi:10.1002/smj.70023.",
    "Carroll, C., Booth, A., Leaviss, J., and Rick, J. (2013). \"Best fit\" framework synthesis: Refining the method. *BMC Medical Research Methodology*, 13, 37.",
    "Cohen, S. K., Caza, B. B., and Jones, C. (2025). From puzzling to plausible: The role of abduction in organizational research. *Academy of Management Discoveries*, 11(4), 469–478. doi:10.5465/amd.2025.0388.",
    "Dew, N. (2009). Serendipity in entrepreneurship. *Organization Studies*, 30(7), 735–753.",
    "Eisenhardt, K. M. (1989). Building theories from case study research. *Academy of Management Review*, 14(4), 532–550. doi:10.5465/amr.1989.4308385.",
    "Gehman, J., Glaser, V. L., Eisenhardt, K. M., Gioia, D., Langley, A., and Corley, K. G. (2018). Finding theory–method fit: A comparison of three qualitative approaches to theory building. *Journal of Management Inquiry*, 27(3), 284–300. doi:10.1177/1056492617706029.",
    "Guest, G., Bunce, A., and Johnson, L. (2006). How many interviews are enough? An experiment with data saturation and variability. *Field Methods*, 18(1), 59–82.",
    "Hennink, M. M., Kaiser, B. N., and Marconi, V. C. (2017). Code saturation versus meaning saturation: How many interviews are enough? *Qualitative Health Research*, 27(4), 591–608.",
    "Hsieh, H.-F., and Shannon, S. E. (2005). Three approaches to qualitative content analysis. *Qualitative Health Research*, 15(9), 1277–1288. doi:10.1177/1049732305276687.",
    "MacQueen, K. M., McLellan, E., Kay, K., and Milstein, B. (1998). Codebook development for team-based qualitative analysis. *Cultural Anthropology Methods*, 10(2), 31–36.",
    "Mirvahedi, S., and Morrish, S. (2017). The role of serendipity in opportunity exploration. *Journal of Research in Marketing and Entrepreneurship*, 19(2), 182–200.",
    "Roberts, K., Dowell, A., and Nie, J.-B. (2019). Attempting rigour and replicability in thematic analysis of qualitative research data: A case study of codebook development. *BMC Medical Research Methodology*, 19. doi:10.1186/s12874-019-0707-y.",
    "Robinson, O. C., and Bailey-Rodriguez, D. (2026). Deductive qualitative research: An integrative approach to designing studies. *Qualitative Research in Psychology*, 23(2), 369–384. doi:10.1080/14780887.2025.2604773.",
    "Sætre, A. S., and Van de Ven, A. H. (2021). Generating theory by abduction. *Academy of Management Review*. doi:10.5465/amr.2019.0233.",
    "Sandberg, J., and Alvesson, M. (2011). Ways of constructing research questions: Gap-spotting or problematization? *Organization*, 18(1), 23–44. doi:10.1177/1350508410372151.",
    "Timmermans, S., and Tavory, I. (2012). Theory construction in qualitative research: From grounded theory to abductive analysis. *Sociological Theory*. doi:10.1177/0735275112457914.",
    "Vila-Henninger, L., et al. (2024). Abductive coding: Theory building and qualitative (re)analysis. *Sociological Methods & Research*, 53(2), 968–1001.",
  ].map((r) => new Paragraph({ children: runs(r), indent: { left: 360, hanging: 360 }, spacing: { after: 80 } })),
];

function gapP() { return new Paragraph({ children: [], spacing: { after: 60 } }); }

const doc = new Document({
  creator: "Vyas Sreenivas", title: "Proposal: an auditable harness for abductive coding with people and AI",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, color: "1F3A5F", font: FONT }, paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 0 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["Proposal draft, 23 October 2026  ·  ", PageNumber.CURRENT], size: 17, color: "777777" })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
