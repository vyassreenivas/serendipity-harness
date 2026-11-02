// Writes the readable pilot codebook from codebook.json (made by export.py).
// Usage: node build_codebook.js codebook.json codebook_pilot.docx   (needs docx@9)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ExternalHyperlink, Footer, PageNumber,
} = require("docx");

const [, , IN, OUT] = process.argv;
const data = JSON.parse(fs.readFileSync(IN, "utf8"));
const FONT = "Calibri", NAVY = "1F3A5F", GREY = "666666";
const SQTEXT = { SQ1: "What counts as serendipity?", SQ2: "Where does it happen, and what sets it off?",
  SQ3: "What do founders bring and do?", SQ4: "What does it change in the venture?",
  SQ5: "When is it more or less likely?", SQ6: "How do founders tell it?", all: "All sub-questions" };

const P = (children, o = {}) => new Paragraph({ children, spacing: { after: 80 }, ...o });
const T = (text, o = {}) => new TextRun({ text, ...o });
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
const cell = (runs, w, head) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders,
  shading: head ? { fill: NAVY, type: ShadingType.CLEAR, color: "auto" } : undefined,
  margins: { top: 50, bottom: 50, left: 90, right: 90 },
  children: [new Paragraph({ children: runs })] });
const H = (t) => T(t, { bold: true, color: "FFFFFF", size: 19 });
const C = (t, o = {}) => T(t, { size: 19, ...o });

const children = [
  new Paragraph({ children: [T("Serendipity codebook, version 1.0 (pilot)", { bold: true, size: 36, color: NAVY })], spacing: { after: 60 } }),
  new Paragraph({ children: [T(`Draft for review by Vyas Sreenivas and Ravi, 20 October 2026. Built from ${data.review}.`, { size: 20, color: GREY })], spacing: { after: 200 } }),
  P([T("How to read it. ", { bold: true }), T("The codebook has 11 groups. Each asks one question of an episode: a stretch of an interview in which something unexpected happens and the founder acts on it. Coders apply the core codes in every group to every episode, and add a misfit code for anything that matters but that no code captures. The examples in quotation marks are made up for illustration; they are not quotes from the interviews.")]),
  P([T("Where the codes come from. ", { bold: true }), T("A model read 107 papers and drafted 360 codes, each tied to the passages it rests on. The researchers chose 43 core codes and rewrote them for founder interviews. Under each code, the five papers with the most supporting passages are quoted: one sentence each, chosen by fixed code as the sentence that best matches the code, copied from the paper with its PDF page. Other supporting papers are listed after them.")]),
  new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [500, 1500, 3000, 3560, 800],
    rows: [new TableRow({ tableHeader: true, children: [cell([H("#")], 500, 1), cell([H("Group")], 1500, 1), cell([H("Sub-question")], 3000, 1), cell([H("Question asked of each episode")], 3560, 1), cell([H("Core")], 800, 1)] }),
      ...data.groups.map((g, i) => new TableRow({ children: [cell([C(String(i + 1))], 500), cell([C(g.name, { bold: true })], 1500),
        cell([C(g.sq === "all" ? SQTEXT.all : `${g.sq} ${SQTEXT[g.sq]}`)], 3000), cell([C(g.asks)], 3560), cell([C(String(g.codes.length))], 800)] }))] }),
  new Paragraph({ children: [T("Table 1. The 11 groups, in sub-question order.", { italics: true, size: 19, color: GREY })], spacing: { before: 60, after: 120 } }),
];

data.groups.forEach((g, i) => {
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: i === 0 || i === 10, children: [T(`${i + 1}. ${g.name}`)] }));
  children.push(P([T(g.asks, { italics: true }), T(`   ${g.sq === "all" ? "All sub-questions" : g.sq + " " + SQTEXT[g.sq]}`, { color: GREY, size: 19 })], { spacing: { after: 140 } }));
  if (g.name === "misfit") {
    children.push(P([T("Each misfit code names the group the material overflows from. Every misfit records a short label in the coder's words, the paragraphs it rests on, and one line on why no code fits. Definition has no misfit code: an episode that may or may not count gets the verdict ‘unresolved’.")]));
  }
  g.codes.forEach((c) => {
    children.push(new Paragraph({ keepNext: true, spacing: { before: 140, after: 40 }, children: [T(c.label, { bold: true, color: NAVY, size: 23 }), T(`   ${c.id}`, { color: GREY, size: 18 })] }));
    if (c.definition) children.push(P([T(c.definition)], { keepNext: true, spacing: { after: 40 } }));
    children.push(P([T("Code it when: ", { bold: true }), T(c.applies_when)], { keepNext: true, spacing: { after: 40 } }));
    if (c.does_not_apply_when) children.push(P([T("Don't use it when: ", { bold: true }), T(c.does_not_apply_when)], { keepNext: c.sources.length > 0, spacing: { after: 40 } }));
    if (c.sources.length) {
      children.push(P([T("Evidence from the papers", { bold: true, size: 19, color: GREY })], { keepNext: true, spacing: { before: 40, after: 20 } }));
      c.sources.forEach((s) => {
        const who = s.url ? new ExternalHyperlink({ link: s.url, children: [T(s.short, { size: 19, color: "1F5FA8", underline: {} })] }) : T(s.short, { size: 19 });
        const runs = s.quote
          ? [T(`“${s.quote.text}” `, { size: 19, italics: true }), T("— ", { size: 19, color: GREY }), who, T(`, p. ${s.quote.pdf_page}`, { size: 19, color: GREY })]
          : [T("(no single sentence states it; see the cited passages) ", { size: 19, color: GREY }), who];
        children.push(new Paragraph({ children: runs, indent: { left: 300 }, spacing: { after: 40 } }));
      });
      if (c.also.length) {
        const runs = [T("Also: ", { bold: true, size: 19, color: GREY })];
        c.also.forEach((s, k) => {
          if (k) runs.push(T("  ·  ", { size: 19, color: GREY }));
          runs.push(s.url ? new ExternalHyperlink({ link: s.url, children: [T(s.short, { size: 19, color: "1F5FA8", underline: {} })] }) : T(s.short, { size: 19 }));
        });
        children.push(new Paragraph({ children: runs, indent: { left: 300 }, spacing: { after: 80 } }));
      }
    }
  });
  if (g.noncore) children.push(P([T(`${g.noncore} further ${g.name} codes are kept as reference, not applied by coders.`, { italics: true, size: 19, color: GREY })], { spacing: { before: 120 } }));
});

const doc = new Document({ creator: "Vyas Sreenivas", title: "Serendipity codebook, version 1.0 (pilot)",
  styles: { default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [{ id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, color: NAVY, font: FONT }, paragraph: { spacing: { before: 320, after: 60 }, outlineLevel: 0 } }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["Serendipity codebook v1.0 (pilot), draft  ·  ", PageNumber.CURRENT], size: 17, color: "777777" })] })] }) },
    children }] });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
