#!/usr/bin/env python3
"""Build the Japanese ASSET Framework manual with macOS native typography."""

from __future__ import annotations

import html
import re
import subprocess
import unicodedata
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/app-manuals/asset-framework-user-manual-ja.md"
OUTPUT = ROOT / "output/pdf/asset-framework-user-manual-ja.pdf"
TMP = ROOT / "tmp/asset-manual"
HTML_FILE = TMP / "asset-framework-user-manual-ja.html"
RAW_PDF = TMP / "asset-framework-user-manual-ja.raw.pdf"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

CSS = r"""
@page cover { size: A4; margin: 0; }
@page manual { size: A4; margin: 18mm 18mm 20mm; }
@font-face { font-family: "Asset Hiragino W3"; src: local("HiraKakuProN-W3"), local("Hiragino Kaku Gothic ProN W3"); font-weight: 300; }
@font-face { font-family: "Asset Hiragino W6"; src: local("HiraKakuProN-W6"), local("Hiragino Kaku Gothic ProN W6"); font-weight: 600; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Asset Hiragino W3", sans-serif; font-weight: 300; color: #102a43; font-size: 10pt; line-height: 1.65; letter-spacing: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.cover { page: cover; width: 210mm; height: 297mm; break-after: page; position: relative; overflow: hidden; background: #fff; }
.cover-rail { position: absolute; inset: 0 auto 0 0; width: 78mm; background-color: #082f49; background-image: linear-gradient(rgba(21,94,117,.45) 1px, transparent 1px), linear-gradient(90deg, rgba(21,94,117,.45) 1px, transparent 1px); background-size: 11mm 11mm; }
.cover-bottom { position: absolute; inset: auto 0 0; height: 8mm; background: #a3e635; }
.signal { position: absolute; width: 66mm; height: 66mm; border: 1.2px solid #22d3ee; border-radius: 50%; opacity: .62; }
.signal::before, .signal::after { content: ""; position: absolute; border: 1.2px solid currentColor; border-radius: 50%; inset: 10mm; }
.signal::after { inset: 22mm; background: currentColor; }
.signal.one { left: 4mm; top: 28mm; color: #22d3ee; } .signal.two { left: 24mm; top: 137mm; color: #a3e635; } .signal.three { left: -8mm; top: 220mm; color: #22d3ee; }
.cover-copy { position: absolute; left: 90mm; right: 14mm; top: 37mm; }
.kicker { color: #0891b2; font-size: 10pt; font-family: "Asset Hiragino W6", sans-serif; font-weight: 600; }
.cover h1 { margin: 16mm 0 0; font-family: "Asset Hiragino W6", sans-serif; font-size: 27pt; line-height: 1.32; font-weight: 600; color: #102a43; }
.cover h1 span { display: block; color: #0891b2; font-size: 25pt; }
.cover-lead { margin: 10mm 0 17mm; color: #526777; font-size: 11pt; }
.benefit { border-left: 2.5mm solid #a3e635; padding-left: 5mm; margin: 0 0 9mm; }
.benefit strong { display: block; font-family: "Asset Hiragino W6", sans-serif; font-weight: 600; font-size: 11pt; } .benefit small { color: #526777; font-size: 9.5pt; }
.cover-meta { position: absolute; left: 90mm; bottom: 20mm; color: #526777; font-size: 9.5pt; }
.manual { page: manual; }
.pagebreak { break-before: page; }
h2 { margin: 4mm 0; padding-left: 4mm; border-left: 2mm solid #a3e635; font-family: "Asset Hiragino W6", sans-serif; font-size: 18pt; line-height: 1.35; font-weight: 600; break-after: avoid; }
h3 { margin: 5mm 0 2.5mm; color: #52820e; font-family: "Asset Hiragino W6", sans-serif; font-size: 13.5pt; line-height: 1.45; font-weight: 600; break-after: avoid; }
p { margin: 0 0 3.2mm; orphans: 3; widows: 3; }
code { color: #007f92; font-family: "Asset Hiragino W6", sans-serif; font-weight: 600; background: #f0f9ff; padding: .15em .35em; border-radius: 2px; }
strong { font-family: "Asset Hiragino W6", sans-serif; font-weight: 600; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 5mm; font-size: 9.2pt; break-inside: auto; }
thead { display: table-header-group; } tr { break-inside: avoid; }
th { padding: 2.1mm 2.5mm; text-align: left; color: #fff; background: #082f49; border-bottom: .7mm solid #0891b2; font-weight: 600; }
td { padding: 2mm 2.5mm; vertical-align: top; border-bottom: .25mm solid #d7e3ea; }
tbody tr:nth-child(even) { background: #f8fbfc; } th:first-child, td:first-child { width: 29%; }
.steps { list-style: none; padding: 0; counter-reset: steps; }
.steps li { counter-increment: steps; position: relative; margin: 0 0 2.5mm; padding: 3mm 4mm 3mm 15mm; border: .25mm solid #d7e3ea; border-left: 1.4mm solid #a3e635; background: #fbfdf7; break-inside: avoid; }
.steps li::before { content: counter(steps); position: absolute; left: 0; top: 0; bottom: 0; width: 11mm; display: grid; place-items: center; color: #fff; background: #65a30d; font-weight: 600; }
ul { margin: 0 0 3mm; padding-left: 6mm; } li::marker { color: #65a30d; }
.callout { margin: 2mm 0 5mm; padding: 3mm 4mm; border: .3mm solid #0891b2; border-left-width: 1.5mm; background: #f0f9ff; break-inside: avoid; }
.callout.warning { border-color: #d97706; background: #fff7ed; } .callout.success { border-color: #65a30d; background: #f7fee7; }
.callout strong { display: block; color: #087e99; } .callout.warning strong { color: #b45309; } .callout.success strong { color: #52820e; }
figure { margin: 4mm auto 6mm; break-inside: avoid; } figure img { display: block; width: 100%; max-height: 104mm; object-fit: contain; border: .25mm solid #b9cbd5; box-shadow: 0 1.5mm 4mm rgba(8,47,73,.14); }
figcaption { margin-top: 2mm; color: #526777; font-size: 8.5pt; text-align: center; }
.toc { margin-top: 5mm; } .toc a { display: grid; grid-template-columns: auto 1fr auto; gap: 2mm; align-items: end; color: #102a43; text-decoration: none; margin: 0 0 2mm; }
.toc a.sub { padding-left: 7mm; color: #526777; font-size: 9.3pt; } .toc .dots { border-bottom: .25mm dotted #9aacb7; transform: translateY(-1.4mm); } .toc .page { color: #52820e; font-weight: 600; }
"""

def anchor_id(text: str) -> str:
    value = re.sub(r"\s+", "-", text.strip().lower())
    return re.sub(r"[^0-9a-zA-Z\-_.\u3040-\u30ff\u3400-\u9fff]", "", value) or "section"

def inline(text: str) -> str:
    value = html.escape(text)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)

def collect_headings(lines: list[str]) -> list[tuple[int, str, str]]:
    seen, headings = {}, []
    for line in lines:
        match = re.match(r"^(#{2,3})\s+(.+)$", line.strip())
        if not match or match.group(2) == "目次": continue
        level, text = len(match.group(1)), match.group(2).strip()
        base = anchor_id(text); seen[base] = seen.get(base, 0) + 1
        headings.append((level, text, base if seen[base] == 1 else f"{base}-{seen[base]}"))
    return headings

def make_toc(headings, pages) -> str:
    rows = ['<nav class="toc">']
    for level, text, key in headings:
        cls = ' class="sub"' if level == 3 else ""
        page = str(pages.get(key, "")) if pages else ""
        rows.append(f'<a{cls} href="#{key}"><span>{inline(text)}</span><span class="dots"></span><span class="page">{page}</span></a>')
    return "\n".join(rows + ["</nav>"])

def markdown_body(lines, headings, toc_pages=None) -> str:
    output, paragraph = [], []
    heading_index = i = 0
    def flush():
        if paragraph:
            output.append(f'<p>{inline(" ".join(x.strip() for x in paragraph))}</p>'); paragraph.clear()
    while i < len(lines):
        line = lines[i].strip()
        if not line: flush(); i += 1; continue
        if line == "<!-- pagebreak -->": flush(); output.append('<div class="pagebreak"></div>'); i += 1; continue
        if line == "[TOC]": flush(); output.append(make_toc(headings, toc_pages)); i += 1; continue
        image = re.match(r"!\[(.*?)\]\((.*?)\)", line)
        if image:
            flush(); src = (SOURCE.parent / image.group(2)).resolve().as_uri()
            output.append(f'<figure><img src="{src}" alt="{html.escape(image.group(1))}"><figcaption>{inline(image.group(1))}</figcaption></figure>'); i += 1; continue
        callout = re.match(r"^>\s*\[(SUCCESS|CHECK|TIP|WARNING)\]\s*(.*)", line)
        if callout:
            flush(); kind, text = callout.groups(); labels = {"SUCCESS":"成功のサイン","CHECK":"確認ポイント","TIP":"使い方のヒント","WARNING":"ご注意"}
            output.append(f'<aside class="callout {kind.lower()}"><strong>{labels[kind]}</strong>{inline(text)}</aside>'); i += 1; continue
        if line.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            if len(rows) > 1 and all(set(c) <= {":", "-"} for c in rows[1]): rows.pop(1)
            output.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>")
            output.extend("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in rows[1:]); output.append("</tbody></table>"); continue
        heading = re.match(r"^(#{2,3})\s+(.+)$", line)
        if heading:
            flush(); level, text = len(heading.group(1)), heading.group(2).strip(); key = "toc" if text == "目次" else headings[heading_index][2]
            if text != "目次": heading_index += 1
            output.append(f'<h{level} id="{key}">{inline(text)}</h{level}>'); i += 1; continue
        if re.match(r"^\d+\.\s+", line):
            flush(); items = []
            while i < len(lines):
                match = re.match(r"^\d+\.\s+(.+)", lines[i].strip())
                if not match: break
                items.append(f"<li>{inline(match.group(1))}</li>"); i += 1
            output.append('<ol class="steps">' + "".join(items) + "</ol>"); continue
        if line.startswith("- "):
            flush(); items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>"); i += 1
            output.append("<ul>" + "".join(items) + "</ul>"); continue
        paragraph.append(line); i += 1
    flush(); return "\n".join(output)

def render_html(lines, pages=None) -> str:
    headings = collect_headings(lines); body = markdown_body(lines, headings, pages)
    cover = """<section class="cover"><div class="cover-rail"><i class="signal one"></i><i class="signal two"></i><i class="signal three"></i></div><div class="cover-bottom"></div><div class="cover-copy"><div class="kicker">VISUAL QUICKSTART</div><h1>ASSET Framework App<span>使用説明書</span></h1><p class="cover-lead">はじめての RSS 予測を、かんたんに。</p><div class="benefit"><strong>かんたん予測</strong><small>地図上でエリアを選ぶだけ</small></div><div class="benefit"><strong>結果をすぐ確認</strong><small>CSV に保存して再利用</small></div><div class="benefit"><strong>やさしい手順</strong><small>初めてでも迷わない</small></div></div><div class="cover-meta">文書版&nbsp;&nbsp;v1.2<br>更新日&nbsp;&nbsp;2026年9月8日</div></section>"""
    return f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>ASSET Framework App 使用説明書 v1.2</title><style>{CSS}</style></head><body>{cover}<main class="manual">{body}</main></body></html>'

def chrome_print():
    if not CHROME.exists(): raise FileNotFoundError(f"Google Chrome was not found: {CHROME}")
    subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer", f"--print-to-pdf={RAW_PDF}", HTML_FILE.as_uri()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def heading_pages(pdf_path, headings):
    texts = [re.sub(r"\s+", "", unicodedata.normalize("NFKC", page.extract_text() or "")) for page in PdfReader(str(pdf_path)).pages]
    result = {}
    for _, title, key in headings:
        needle = re.sub(r"\s+", "", unicodedata.normalize("NFKC", title.replace("`", "").replace("**", "")))
        candidates = list(enumerate(texts[3:], 4))
        if title == "このマニュアルの進み方": candidates = list(enumerate(texts[1:], 2))
        for number, text in candidates:
            if needle in text: result[key] = number; break
    return result

def finish_pdf(raw_pdf, output, headings, pages):
    reader, writer = PdfReader(str(raw_pdf)), PdfWriter(); width, _ = A4
    toc_links = []
    for number, page in enumerate(reader.pages, 1):
        if number in (2, 3):
            for annotation in page.get("/Annots", []):
                item = annotation.get_object(); destination = item.get("/Dest")
                if destination:
                    toc_links.append((number-1, tuple(float(x) for x in item["/Rect"]), unquote(str(destination).lstrip("/"))))
            page.pop("/Annots", None)
        if number > 1:
            stream = BytesIO(); overlay = canvas.Canvas(stream, pagesize=A4)
            overlay.setFillColorRGB(.031, .184, .286); overlay.rect(0, A4[1]-11*72/25.4, width, 11*72/25.4, fill=1, stroke=0)
            overlay.setFillColorRGB(.639, .902, .208); overlay.rect(0, A4[1]-11*72/25.4, 28*72/25.4, 11*72/25.4, fill=1, stroke=0)
            overlay.setFont("Helvetica", 7.8); overlay.setFillColorRGB(1, 1, 1); overlay.drawString(34*72/25.4, A4[1]-7.2*72/25.4, "ASSET Framework App  |  VISUAL QUICKSTART")
            overlay.setStrokeColorRGB(.843, .89, .918); overlay.line(18*72/25.4, 16*72/25.4, width-18*72/25.4, 16*72/25.4)
            overlay.setFont("Helvetica", 8.5); overlay.setFillColorRGB(.32, .40, .46); overlay.drawString(18*72/25.4, 11*72/25.4, "ASSET Framework App User Manual")
            overlay.setFillColorRGB(.322, .51, .055); overlay.drawRightString(width - 18*72/25.4, 11*72/25.4, f"{number:02d}")
            overlay.save(); stream.seek(0); page.merge_page(PdfReader(stream).pages[0])
        writer.add_page(page)
    for source_page, rect, key in toc_links:
        if key in pages:
            writer.add_annotation(source_page, Link(rect=rect, target_page_index=pages[key]-1))
    parent = None
    for level, title, key in headings:
        if key not in pages: continue
        item = writer.add_outline_item(title, pages[key]-1, parent=parent if level == 3 else None)
        if level == 2: parent = item
    writer.add_metadata({"/Title":"ASSET Framework App 使用説明書 v1.2","/Author":"ASSET Framework"}); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle: writer.write(handle)

def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True); lines = SOURCE.read_text(encoding="utf-8").splitlines(); lines = lines[lines.index("<!-- pagebreak -->")+1:]; headings = collect_headings(lines)
    HTML_FILE.write_text(render_html(lines), encoding="utf-8"); chrome_print(); pages = heading_pages(RAW_PDF, headings)
    HTML_FILE.write_text(render_html(lines, pages), encoding="utf-8"); chrome_print(); pages = heading_pages(RAW_PDF, headings); finish_pdf(RAW_PDF, OUTPUT, headings, pages)
    print(OUTPUT); return 0

if __name__ == "__main__": raise SystemExit(main())
