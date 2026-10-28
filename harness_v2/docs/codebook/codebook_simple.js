// Build the codebook (both levels) as a Word document from codebook_simple.json.
// Usage: node codebook_simple.js codebook_simple.json codebook_simple.docx   (needs the docx package, version 9)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, PageOrientation, LevelFormat, AlignmentType, Footer, PageNumber,
} = require("docx");

const [, , IN, OUT] = process.argv;
const D = JSON.parse(fs.readFileSync(IN, "utf8"));
const NAVY = "1F3A5F", PLUM = "6A3D7A", GREY = "666666", TINT = "EEF2F6", PLUMTINT = "F4EEF6";
const unq = (s) => String(s || "").replace(/^['“"]|['”"]$/g, "");
const border = { style: BorderStyle.SINGLE, size: 4, color: "C8CFCD" };
const borders = { top: border, bottom: border, left: border, right: border };
const t = (text, o = {}) => new TextRun({ text, size: 19, ...o });

function cell(paras, w, fill) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: paras.map((runs) => new Paragraph({ children: runs })),
  });
}
function table(widths, head, rows) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: head.map((h, i) => cell([[t(h, { bold: true, color: "FFFFFF" })]], widths[i], NAVY)) }),
      ...rows.map((r) => new TableRow({ children: r.cells.map((c, i) => cell(c, widths[i], r.fill)) }))],
  });
}
const P = (runs, o = {}) => new Paragraph({ children: runs, spacing: { after: 100 }, ...o });
const H = (text, level = HeadingLevel.HEADING_2, color = NAVY) => new Paragraph({ heading: level, spacing: { before: 260, after: 80 },
  children: [new TextRun({ text, color })] });
const B = (runs) => new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 50 }, children: runs });

const GW = (o = {}) => t("", o);
const W1 = [700, 2300, 4260, 2100];   // no., code, what it captures, sources (portrait width 9360)
const codeRow = (c) => ({ cells: [[[t(c.no, { color: GREY })]], [[t(c.label, { bold: true })]], [[t(c.captures)]], [[t(c.papers, { size: 17 })]]] });
function band(text, w) {  // a shaded row across the table
  return new TableRow({ children: [new TableCell({ columnSpan: 4, width: { size: w, type: WidthType.DXA }, borders,
    shading: { fill: TINT, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ children: [t(text, { bold: true, color: NAVY, size: 18 })] })] })] });
}
function codeTable(g) {
  const w = W1.reduce((x, y) => x + y);
  const head = new TableRow({ tableHeader: true, children: ["No.", "Code", "What it captures", "Sources"].map((h, i) => cell([[t(h, { bold: true, color: "FFFFFF" })]], W1[i], NAVY)) });
  const row = (r) => new TableRow({ children: r.cells.map((c, i) => cell(c, W1[i], r.fill)) });
  const rows = [head];
  if (g.pick_one) {
    rows.push(band(`${g.pick_one.name} (pick one): ${g.pick_one.asks}`, w), ...g.pick_one.options.map(codeRow).map(row));
    rows.push(band("Parts present (tick each that applies)", w));
  }
  rows.push(...g.codes.map(codeRow).map(row));
  if (g.anomaly) rows.push(row({ fill: PLUMTINT, cells: [[[t(g.anomaly.no, { color: GREY })]], [[t("None of these fits", { bold: true, color: PLUM }), t(" (anomaly code)", { color: PLUM, size: 17 })]],
    [[t(g.anomaly.captures + ". The coder records a short label, the passages and why no code fits.")]], [[t("")]]] }));
  return new Table({ width: { size: w, type: WidthType.DXA }, columnWidths: W1, rows });
}

const total = D.structure.reduce((n, s) => n + s.codes, 0);
const children = [
  new Paragraph({ children: [new TextRun({ text: "Serendipity codebook", bold: true, size: 36, color: NAVY })], spacing: { after: 40 } }),
  P([t(`Version 1.0. Vyas Sreenivas and Ravi S. Kudesia. Built ${D.built} from the codebook workbook. The codebook trail lists every paper and sentence behind each code.`, { color: GREY })]),
  H("How the codebook is organised", HeadingLevel.HEADING_1),
  P([t("The research question is broken into six sub-questions. Each sub-question is answered by one or two groups, and each group asks one question of an interview. A group holds the codes that answer it. Codes are numbered by group: 2.3 is the third code of group 2.")]),
  table([1300, 4060, 2800, 1200], ["Sub-question", "", "Groups", "Codes"],
    [...D.structure.map((s) => ({ cells: [[[t(s.sq.replace("SQ", ""), { bold: true })]], [[t(s.text)]], s.groups.map((g) => [t(g)]), [[t(String(s.codes))]]] })),
     { fill: TINT, cells: [[[t("")]], [[t("Level 1 in all", { bold: true })]], [[t(`${D.counts.groups} groups`)]], [[t(String(total), { bold: true })]]] }]),
  H("Two levels", HeadingLevel.HEADING_2),
  B([t("Level 1: what coders tick. ", { bold: true }), t(`${D.counts.level1} codes for things a coder can point to in a sentence or two of an interview. Each tick cites the passages it rests on.`)]),
  B([t("Level 2: what is worked out afterwards. ", { bold: true }), t(`${D.counts.level2} items. Nine are rules over level-1 codes, joined by AND, OR and NOT; two are judgments the researchers make with a written reason. No one ticks a level-2 item, so no coder decides whether a story is serendipity.`)]),
  B([t("Anomaly codes. ", { bold: true }), t(`Groups 2 to ${D.counts.groups} each end with an anomaly code for what the group's codes miss, and one more takes what no group asks about. Group 1 has none: its search state allows "unclear".`)]),
  P([t("Coders code the whole interview, ticking a code wherever a passage shows it. Each tick names the story it belongs to: one thread of the founder's journey, such as \"the café order\". Level 2 is worked out story by story.", { color: GREY })], { spacing: { before: 80, after: 100 } }),
  H(`Level 1: what coders tick (${D.counts.level1} codes)`, HeadingLevel.HEADING_1),
];

D.level1.forEach((g) => {
  children.push(H(`${g.no}. ${g.name}`));
  children.push(P([t(`Sub-question ${g.sq.replace("SQ", "")}: ${g.sq_text}  `, { color: GREY }), t("Coders ask: ", { color: GREY }), t(g.asks, { italics: true })]));
  children.push(codeTable(g));
});
children.push(H(`${D.counts.groups + 1}. Something else`));
children.push(P([t("Coders ask: ", { color: GREY }), t("Is there something relevant that no group asks about?", { italics: true })]));
children.push(codeTable({ codes: [], anomaly: D.new }));

children.push(H(`Level 2: worked out afterwards (${D.counts.level2} items)`, HeadingLevel.HEADING_1));
children.push(P([t("Each rule is applied to one coder's level-1 ticks for one story. The numbers in brackets are the level-1 codes.", { color: GREY })]));
D.level2.forEach((part) => {
  children.push(H(part.part));
  children.push(table([600, 2500, 4160, 2100], ["No.", "Item", "Rule", "Sources"],
    part.rows.map((r) => ({ cells: [[[t(r.no, { color: GREY })]], [[t(r.name, { bold: true })], [t(r.in_short, { color: GREY, size: 17 })]], [[t(r.rule)]], [[t(r.papers, { size: 17 })]]] }))));
});

const doc = new Document({
  creator: "Vyas Sreenivas", title: "Serendipity codebook, version 1.0",
  styles: { default: { document: { run: { font: "Calibri", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, color: NAVY, font: "Calibri" }, paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: "Calibri" }, paragraph: { spacing: { before: 220, after: 80 }, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "Serendipity codebook, version 1.0  ·  page ", size: 16, color: "888888" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
