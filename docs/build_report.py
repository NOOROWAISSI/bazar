"""Rebuild design.pdf: pip install reportlab; python docs/build_report.py."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak


def main():
    root = Path(__file__).resolve().parent
    styles = {
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.7,
                               leading=13.6, spaceAfter=7, alignment=TA_LEFT),
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20,
                                leading=24, textColor=colors.HexColor("#164658"), spaceAfter=12),
        "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12,
                                  leading=15, textColor=colors.HexColor("#164658"),
                                  spaceBefore=9, spaceAfter=7, keepWithNext=True),
    }
    story, paragraph = [], []
    def flush():
        if paragraph:
            story.append(Paragraph(escape(" ".join(paragraph)), styles["body"]))
            paragraph.clear()
    for line in (root / "design.md").read_text(encoding="utf-8").splitlines():
        if line == "<!-- pagebreak -->":
            flush(); story.append(PageBreak())
        elif line.startswith("# "):
            flush(); story.append(Paragraph(escape(line[2:]), styles["title"]))
        elif line.startswith("## "):
            flush(); story.append(Paragraph(escape(line[3:]), styles["heading"]))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
    flush()
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#b9cbd0"))
        canvas.line(48, 36, A4[0]-48, 36)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#526773"))
        canvas.drawString(48, 24, "Bazar.com | Distributed and Operating Systems | Noor and Sara")
        canvas.drawRightString(A4[0]-48, 24, f"{doc.page} / 3")
    document = SimpleDocTemplate(str(root / "design.pdf"), pagesize=A4,
        rightMargin=48, leftMargin=48, topMargin=38, bottomMargin=48,
        title="Bazar.com - Design and execution report", author="Noor and Sara")
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print("Created", root / "design.pdf")


if __name__ == "__main__":
    main()
