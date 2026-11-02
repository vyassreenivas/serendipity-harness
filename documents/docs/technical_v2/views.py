"""Build the two HTML views of technical document v2. Single files, images inside.

Usage: python views.py
  technical_draft.html  the draft (technical_draft.md), readable in any browser
  process.html          every step of the harness, from process.json: who does it,
                        where we decide, the files and the record it leaves
The draft is written in Markdown while it is being built; the Word version comes
once it is final. This converter handles only what the draft uses: headings,
paragraphs, numbered lists, tables, images, bold and italic.
"""
import base64
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
E = html.escape
STYLE = """
:root{--ink:#1a1a1a;--soft:#5a5a5a;--line:#dcdcdc;--bg:#fff;--tint:#f5f6f8;--navy:#1f3a5f;
--us:#d7ebd5;--model:#fbe3c4;--program:#dce6f2;--check:#2f6b3a}
@media (prefers-color-scheme:dark){:root{--ink:#e8e8e8;--soft:#a8a8a8;--line:#3a3a3a;--bg:#16181c;--tint:#20242a;--navy:#8fb3e0;
--us:#2c4a2a;--model:#5a4020;--program:#23364d;--check:#8fd19e}}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Georgia,serif}
main{max-width:860px;margin:0 auto;padding:28px 16px 80px} h1{font:600 28px/1.25 system-ui,sans-serif;color:var(--navy);margin:0 0 6px}
h2{font:600 20px/1.3 system-ui,sans-serif;color:var(--navy);margin:34px 0 8px;padding-top:10px;border-top:1px solid var(--line)}
p,li{max-width:72ch} img{max-width:100%;background:#fff;border-radius:6px;margin:10px 0 2px}
table{border-collapse:collapse;width:100%;font:14px/1.45 system-ui,sans-serif;margin:10px 0}
th{background:var(--navy);color:#fff;text-align:left;padding:6px 8px} td{border-top:1px solid var(--line);padding:6px 8px;vertical-align:top}
.cap{font-size:14px;color:var(--soft)} .empty{color:var(--soft);font-style:italic}
"""


def inline(t):
    t = E(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)


def image(path):
    data = base64.b64encode((HERE / path).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="">'


def markdown(md):
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
            nxt = next((l for l in lines[i + 1:] if l.strip()), "")
            if nxt.startswith("## "):
                out.append('<p class="empty">To be written.</p>')
            i += 1
        elif line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>"); i += 1
        elif line.startswith("!["):
            out.append(image(re.search(r"\((.+?)\)", line).group(1))); i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                if not set("".join(cells)) <= set("-: "):
                    rows.append(cells)
                i += 1
            head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            out.append(f"<table><tr>{head}</tr>{body}</table>")
        elif re.match(r"\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append(f"<li>{inline(lines[i].split('. ', 1)[1])}</li>"); i += 1
            out.append(f"<ol>{''.join(items)}</ol>")
        else:
            cls = ' class="cap"' if line.startswith("*Figure") or line.startswith("*Table") else ""
            out.append(f"<p{cls}>{inline(line)}</p>"); i += 1
    return "\n".join(out)


def page(title, body, extra=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{E(title)}</title><style>{STYLE}{extra}</style></head><body><main>{body}</main></body></html>")


PROCESS_STYLE = """
main{max-width:1100px}
.legend span{display:inline-block;padding:2px 10px;border-radius:4px;margin-right:6px;font:13px system-ui,sans-serif}
.us{background:var(--us)} .model{background:var(--model)} .program{background:var(--program)}
.phase{margin-top:26px} .box{background:var(--tint);border-radius:8px;padding:10px 14px;font:14px/1.5 system-ui,sans-serif}
.step td:first-child{font:600 13px system-ui,sans-serif;white-space:nowrap} code{font-size:12.5px}
.dec{color:var(--check);font-weight:700;white-space:nowrap} .st{font-size:12.5px;color:var(--soft)}
"""


def files(paths):
    return "<br>".join(f'<code title="{E(f)}">{E(Path(f).name)}</code>' for f in paths)


def process():
    P = json.loads((HERE / "process.json").read_text(encoding="utf-8"))
    who = P["who"]
    body = ['<h1>How the harness works</h1>',
            '<p>Every step of the harness, in order. Each is done by us, by the model or by a program, and each leaves a record. '
            'Outlined steps are where we decide. The same steps are drawn in Figures 3 and 4 of the technical draft.</p>',
            '<p class="legend">' + "".join(f'<span class="{k}">{E(v["name"])}</span>' for k, v in who.items()) + "</p>",
            "<table>" + "".join(f'<tr><td class="{k}"><b>{E(v["name"])}</b></td><td>{E(v["why"])}</td></tr>' for k, v in who.items()) + "</table>"]
    for ph in P["phases"]:
        rows = "".join(
            f'<tr class="step"><td>{n}</td><td class="{s["who"]}">{E(who[s["who"]]["name"])}</td>'
            f'<td>{E(s["what"])}{" <span class=dec>we decide</span>" if s.get("check") else ""}</td>'
            f'<td>{files(s["files"])}</td><td>{E(s["record"])}</td>'
            f'<td class="st">{E(s["status"])}</td></tr>'
            for n, s in enumerate(ph["steps"], 1))
        body.append(f'<section class="phase"><h2>{E(ph["stage"])}. {E(ph["name"])}</h2>'
                    f'<p class="box">{E(ph["containers"])}</p>'
                    f"<table><tr><th>#</th><th>Who</th><th>Step</th><th>Files</th><th>Record</th><th>Status</th></tr>{rows}</table>"
                    f'<p><b>Out:</b> {E(ph["out"])}</p></section>')
    return page("How the harness works", "".join(body), PROCESS_STYLE)


if __name__ == "__main__":
    md = (HERE / "technical_draft.md").read_text(encoding="utf-8")
    (HERE / "technical_draft.html").write_text(page("Technical appendix, draft 2", markdown(md)), encoding="utf-8")
    (HERE / "process.html").write_text(process(), encoding="utf-8")
    print("wrote technical_draft.html, process.html")
