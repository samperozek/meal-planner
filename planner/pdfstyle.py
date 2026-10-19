"""Styles for the weekly plan PDF (ReportLab). Uses Georgia/Arial on macOS, Helvetica/Times elsewhere."""
import os, re
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

F = "/System/Library/Fonts/Supplemental/"
if os.path.exists(F + "Georgia.ttf"):
    for name, file in [("Serif", "Georgia.ttf"), ("Serif-Bold", "Georgia Bold.ttf"), ("Serif-Italic", "Georgia Italic.ttf"),
                       ("Sans", "Arial.ttf"), ("Sans-Bold", "Arial Bold.ttf"), ("Sans-Italic", "Arial Italic.ttf")]:
        pdfmetrics.registerFont(TTFont(name, F + file))
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans-Italic", boldItalic="Sans-Bold")
    pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold", italic="Serif-Italic", boldItalic="Serif-Bold")
    SANS, SANS_B, SERIF, SERIF_B, SERIF_I = "Sans", "Sans-Bold", "Serif", "Serif-Bold", "Serif-Italic"
else:
    SANS, SANS_B, SERIF, SERIF_B, SERIF_I = "Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold", "Times-Italic"

WINE = colors.HexColor("#7A2331"); INK = colors.HexColor("#22201E"); MUTED = colors.HexColor("#6B645C")
CREAM = colors.HexColor("#F6F1E9"); SAGE = colors.HexColor("#EEF2EA"); SAGE_D = colors.HexColor("#4F6B45")
RULE = colors.HexColor("#D9CFC1")

S = {
    "kicker": ParagraphStyle("kicker", fontName=SANS_B, fontSize=8, leading=10, textColor=WINE, spaceAfter=4),
    "title": ParagraphStyle("title", fontName=SERIF_B, fontSize=22, leading=26, textColor=INK, spaceAfter=2),
    "native": ParagraphStyle("native", fontName=SERIF_I, fontSize=11.5, leading=15, textColor=MUTED, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=SERIF_B, fontSize=13, leading=16, textColor=WINE, spaceBefore=10, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName=SANS_B, fontSize=9, leading=12, textColor=INK, spaceBefore=5, spaceAfter=2),
    "body": ParagraphStyle("body", fontName=SANS, fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=4),
    "small": ParagraphStyle("small", fontName=SANS, fontSize=8, leading=10.5, textColor=MUTED),
    "item": ParagraphStyle("item", fontName=SANS, fontSize=9.3, leading=12.6, textColor=INK, leftIndent=9, firstLineIndent=-9, spaceAfter=1.5),
    "boxh": ParagraphStyle("boxh", fontName=SANS_B, fontSize=9.3, leading=12, textColor=SAGE_D),
    "box": ParagraphStyle("box", fontName=SANS, fontSize=9, leading=12.6, textColor=INK),
}
W = letter[0] - 1.3 * inch


def esc(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"&lt;(/?)(b|i)&gt;", r"<\1\2>", t)


def P(t, st="body"):
    return Paragraph(t, S[st])   # raw markup: callers esc() their data


def boxed(rows_flow, bg=SAGE, edge=SAGE_D):
    t = Table([[f] for f in rows_flow], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 2.5, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9)]))
    return t
