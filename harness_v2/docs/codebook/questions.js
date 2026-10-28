// Build the research question and sub-questions page as a Word document from questions.json.
// Usage: node questions.js questions.json questions.docx   (needs the docx package, version 9)
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle } = require("docx");

const [, , IN, OUT] = process.argv;
const D = JSON.parse(fs.readFileSync(IN, "utf8"));
const NAVY = "1F3A5F", GREY = "666666";
const border = { style: BorderStyle.SINGLE, size: 4, color: "C8CFCD" };
const borders = { top: border, bottom: border, left: border, right: border };
const t = (text, o = {}) => new TextRun({ text, size: 19, ...o });
const W = [600, 5460, 3300];
const cell = (paras, w, fill) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders,
  shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined, margins: { top: 60, bottom: 60, left: 90, right: 90 },
  children: paras.map((runs) => new Paragraph({ children: runs })) });

const rows = D.rows.map((r) => new TableRow({ cantSplit: true, children: [
  [[t(r.sq, { bold: true })]],
  [[t(r.text)]],
  r.read_for.map((g) => [t(g)]),
].map((c, i) => cell(c, W[i])) }));

const doc = new Document({
  creator: "Vyas Sreenivas", title: "Research question and sub-questions",
  styles: { default: { document: { run: { font: "Calibri", size: 20 } } } },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } } },
    children: [
      new Paragraph({ children: [new TextRun({ text: "Research question and sub-questions", bold: true, size: 34, color: NAVY })], spacing: { after: 200 } }),
      new Paragraph({ children: [t("Research question", { bold: true, color: NAVY })], spacing: { after: 60 } }),
      new Paragraph({ children: [t(D.question, { italics: true, size: 24 })], spacing: { after: 60 } }),
      new Paragraph({ children: [t(D.kind, { color: GREY })], spacing: { after: 240 } }),
      new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: W, rows: [
        new TableRow({ tableHeader: true, children: ["", "Sub-question", "What we looked for in the papers"].map((h, i) => cell([[t(h, { bold: true, color: "FFFFFF" })]], W[i], NAVY)) }),
        ...rows] }),
    ] }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
