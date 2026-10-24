// Build the short codebook as a Word document from codebook_simple.json.
// Usage: node codebook_simple.js codebook_simple.json codebook_simple.docx   (needs the docx package, version 9)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, PageOrientation, LevelFormat, AlignmentType, Footer, PageNumber,
} = require("docx");

const [, , IN, OUT] = process.argv;
const D = JSON.parse(fs.readFileSync(IN, "utf8"));
const FONT = "Calibri", NAVY = "1F3A5F", PLUM = "6A3D7A";
const unq = (s) => String(s || "").replace(/^['“"]|['”"]$/g, "");
const cap = (s) => s[0].toUpperCase() + s.slice(1);

const border = { style: BorderStyle.SINGLE, size: 4, color: "C8CFCD" };
const borders = { top: border, bottom: border, left: border, right: border };
const W = [2500, 3900, 2700, 3160, 700];   // landscape text width 12960
function cell(parts, w, opts = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [new Paragraph({ children: parts })],
  });
}
const t = (text, o = {}) => new TextRun({ text, size: 19, ...o });
const head = ["Code", "Code it when", "Example (made up)", "Not when", "Papers"].map((h, i) =>
  cell([t(h, { bold: true, color: "FFFFFF" })], W[i], { fill: NAVY }));

function groupTable(g) {
  const rows = g.codes.map((c) => new TableRow({ children: [
    cell([t(c.label, { bold: true }), t(`  ${c.id}`, { size: 15, color: "777777" })], W[0]),
    cell([t(c.when)], W[1]),
    cell([t(unq(c.example), { italics: true })], W[2]),
    cell([t(c.notwhen)], W[3]),
    cell([t(String(c.papers))], W[4]),
  ] }));
  if (g.anomaly) rows.push(new TableRow({ children: [
    cell([t("None of these fits", { bold: true, color: PLUM }), t(`  ${g.anomaly.id}`, { size: 15, color: "777777" })], W[0], { fill: "F4EEF6" }),
    cell([t(g.anomaly.when + ". Write why no code fits.")], W[1], { fill: "F4EEF6" }),
    cell([t("")], W[2], { fill: "F4EEF6" }),
    cell([t(g.anomaly.notwhen || "")], W[3], { fill: "F4EEF6" }),
    cell([t("")], W[4], { fill: "F4EEF6" }),
  ] }));
  return new Table({ width: { size: 12960, type: WidthType.DXA }, columnWidths: W,
    rows: [new TableRow({ tableHeader: true, children: head }), ...rows] });
}

const P = (text, o = {}) => new Paragraph({ children: [new TextRun({ text, ...o })], spacing: { after: 100 } });
const B = (text) => new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 60 },
  children: text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((x) => x.startsWith("**") ? new TextRun({ text: x.slice(2, -2), bold: true }) : new TextRun(x)) });

const children = [
  new Paragraph({ children: [new TextRun({ text: "Serendipity codebook", bold: true, size: 36, color: NAVY })], spacing: { after: 60 } }),
  P(`The short codebook for coding founder interviews: ${D.core} core codes and ${D.anomalies} anomaly codes in ${D.groups.length + 1} groups. Draft for review by Vyas Sreenivas and Ravi S. Kudesia, built ${D.built} from the codebook workbook.`, { color: "555555", size: 20 }),
  new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("How to use it")] }),
  B("**Code one episode at a time:** a stretch of an interview where something unexpected happens and the founder acts on it."),
  B("**Ask each group's question in turn,** and mark every core code that applies. A group can take several codes. Type takes one (proposed)."),
  B("**If something matters but no code in the group fits,** use the group's anomaly code (\"None of these fits\") and write why. Anomalies are where the literature may be missing something."),
  B("**Tie each code to the words it rests on** in the interview."),
  B("**Papers** is how many papers state the code. The sentences, pages and links are in the codebook workbook and the codebook page."),
];
D.groups.forEach((g) => {
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 80 },
    children: [new TextRun({ text: `${g.n}. ${cap(g.name)}: `, color: NAVY }), new TextRun({ text: g.asks, bold: false })] }));
  children.push(groupTable(g));
  if (g.name === "definition" && D.definitions) children.push(
    new Paragraph({ spacing: { before: 160, after: 60 }, children: [new TextRun({ text: "Definitions: do not tick these. ", bold: true, color: NAVY }),
      new TextRun("An episode meets a definition when every code it needs is ticked; the coding page shows which.")] }),
    new Table({ width: { size: 12960, type: WidthType.DXA }, columnWidths: [3000, 2700, 6560, 700],
      rows: [new TableRow({ tableHeader: true, children: ["Definition", "In short", "Met when these are all ticked", "Papers"].map((h, i) =>
        cell([t(h, { bold: true, color: "FFFFFF" })], [3000, 2700, 6560, 700][i], { fill: NAVY })) }),
        ...D.definitions.map((d) => new TableRow({ children: [cell([t(d.name, { bold: true })], 3000), cell([t(d.in_short)], 2700),
          cell([t(d.needs.join(" + "))], 6560), cell([t(String(d.papers))], 700)] }))] }));
});
children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 80 },
  children: [new TextRun({ text: `${D.groups.length + 1}. Something else: `, color: NAVY }), new TextRun("Is there something relevant that no group asks about?")] }));
children.push(new Paragraph({ children: [new TextRun({ text: `${D.new.id}  `, bold: true, color: PLUM }), new TextRun(D.new.when + ". "),
  new TextRun({ text: "Not when: ", italics: true }), new TextRun(D.new.notwhen || "")] }));

const doc = new Document({
  creator: "Vyas Sreenivas", title: "Serendipity codebook (short)",
  styles: { default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [{ id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 24, bold: true, font: FONT }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840, orientation: PageOrientation.LANDSCAPE },
      margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "Serendipity codebook, draft  ·  page ", size: 16, color: "888888" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
