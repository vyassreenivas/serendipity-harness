// Build the list of papers behind the codebook, each with why it is relevant, as a Word document.
// The codes each paper supports are on the codebook trail.
// Usage: node paper_list.js paper_list.json paper_list.docx   (needs the docx package, version 9)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, AlignmentType, Footer, PageNumber, ExternalHyperlink,
} = require("docx");

const [, , IN, OUT, MODE] = process.argv;  // MODE "core": the core papers only
const D = JSON.parse(fs.readFileSync(IN, "utf8"));
const NAVY = "1F3A5F", GREY = "666666";
const border = { style: BorderStyle.SINGLE, size: 4, color: "C8CFCD" };
const borders = { top: border, bottom: border, left: border, right: border };
const t = (text, o = {}) => new TextRun({ text, size: 18, ...o });

function cell(paras, w, fill) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: paras.map((runs) => new Paragraph({ children: runs })),
  });
}
const ref = (w) => [[t(w.short, { bold: true })], [t(w.text, { size: 16 })],
  ...(w.url ? [[new ExternalHyperlink({ link: w.url, children: [t(w.url.replace("https://doi.org/", "doi: "), { size: 15, color: "1F5FA8" })] })]] : [])];

const W = [4800, 4560];  // portrait width 9360
const band = (text) => new TableRow({ children: [new TableCell({ columnSpan: 2, width: { size: 9360, type: WidthType.DXA }, borders,
  shading: { fill: "EEF2F6", type: ShadingType.CLEAR, color: "auto" }, margins: { top: 50, bottom: 50, left: 90, right: 90 },
  children: [new Paragraph({ children: [t(text, { bold: true, color: NAVY })] })] })] });
const row = (w) => new TableRow({ cantSplit: true, children: [ref(w), [[t(w.why)]]].map((c, i) => cell(c, W[i])) });
const WC = [4200, 5160];
const coreRow = (w) => new TableRow({ cantSplit: true, children: [ref(w), [[t(w.why)]]].map((c, i) => cell(c, WC[i])) });
const TITLE = MODE === "core" ? "Core papers behind the serendipity codebook" : "Papers behind the serendipity codebook";
const WQ = [900, 8460];
const children = MODE === "core" ? [
  new Paragraph({ children: [new TextRun({ text: TITLE, bold: true, size: 34, color: NAVY })], spacing: { after: 160 } }),
  new Paragraph({ children: [t("Research question: ", { bold: true, color: NAVY }), t(D.core.question, { italics: true })], spacing: { after: 100 } }),
  new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: WQ, rows: [
    new TableRow({ tableHeader: true, children: ["SQ", "Sub-question"].map((h, i) => cell([[t(h, { bold: true, color: "FFFFFF" })]], WQ[i], NAVY)) }),
    ...D.core.sub_questions.map((q) => new TableRow({ children: [[[t(q.sq, { bold: true })]], [[t(q.text)]]].map((c, i) => cell(c, WQ[i])) })),
  ] }),
  new Paragraph({ children: [], spacing: { after: 200 } }),
  new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: WC, rows: [
    new TableRow({ tableHeader: true, children: ["Reference", "Why it is relevant"].map((h, i) => cell([[t(h, { bold: true, color: "FFFFFF" })]], WC[i], NAVY)) }),
    ...D.core.papers.map(coreRow),
  ] }),
] : [
  new Paragraph({ children: [new TextRun({ text: TITLE, bold: true, size: 34, color: NAVY })], spacing: { after: 160 } }),
  new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: W, rows: [
    new TableRow({ tableHeader: true, children: ["Reference", "Why it is relevant"].map((h, i) => cell([[t(h, { bold: true, color: "FFFFFF" })]], W[i], NAVY)) }),
    ...D.used.map(row),
    band(`Read, but no code in the codebook rests on it (${D.unused.length})`),
    ...D.unused.map(row),
  ] }),
];

const doc = new Document({
  creator: "Vyas Sreenivas", title: TITLE,
  styles: { default: { document: { run: { font: "Calibri", size: 20 } } },
    paragraphStyles: [{ id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 26, bold: true, color: NAVY, font: "Calibri" }, paragraph: { spacing: { before: 300, after: 100 }, outlineLevel: 0 } }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: `${TITLE}  ·  page `, size: 16, color: "888888" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
