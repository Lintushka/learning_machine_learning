"""Создаёт эталонные docx-стили (ref-ru.docx, ref-en.docx) для pandoc."""
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

HERE = Path(__file__).parent


def build(lang: str, font: str, indent_cm: float, align):
    base = HERE / "_default.docx"
    subprocess.run(["pandoc", "-o", str(base), "--print-default-data-file",
                    "reference.docx"], check=True)
    doc = Document(base)
    styles = doc.styles

    def para(name, indent=None, alignment=None, size=12, bold=False,
             before=0, after=0, page_break=False):
        try:
            s = styles[name]
        except KeyError:
            s = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s.font.name = font
        s.font.size = Pt(size)
        s.font.bold = bold
        s.font.italic = False
        s.font.color.rgb = None
        pf = s.paragraph_format
        pf.first_line_indent = Cm(indent) if indent is not None else Cm(0)
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = 1.15
        pf.page_break_before = page_break
        if alignment is not None:
            pf.alignment = alignment
        return s

    for name in ("Normal", "Body Text", "Compact"):
        para(name, indent=indent_cm, alignment=align)
    para("First Paragraph", indent=0, alignment=align)
    para("Scene Break", indent=0, alignment=WD_ALIGN_PARAGRAPH.CENTER,
         before=12, after=12)
    for name in ("Heading 1", "Heading 2"):
        para(name, indent=0, alignment=WD_ALIGN_PARAGRAPH.CENTER, size=16,
             bold=True, before=24, after=18, page_break=True)
    for name in ("Title", "Subtitle", "Author"):
        para(name, indent=0, alignment=WD_ALIGN_PARAGRAPH.CENTER, size=18)

    doc.save(HERE / f"ref-{lang}.docx")
    base.unlink()


build("ru", "Times New Roman", 1.25, WD_ALIGN_PARAGRAPH.JUSTIFY)
build("en", "Garamond", 0.76, WD_ALIGN_PARAGRAPH.JUSTIFY)  # 0.3 дюйма
print("ok")
