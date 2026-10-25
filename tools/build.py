"""Сборка книги: python3 tools/build.py [ru|en] (без аргумента — обе).

ru: build/ru/book.docx (Литрес, Ridero), book.fb2 (Author.Today, Литрес), book.epub
en: build/en/book.docx (KDP, Draft2Digital), book.epub
"""
import subprocess
import sys
from pathlib import Path

from docx import Document

import typography

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def chapters(lang: str) -> list[Path]:
    return sorted(p for p in (ROOT / lang).glob("[0-9]*.md"))


def fix_after_scene_breaks(docx: Path):
    """Абзац после разделителя сцен — без отступа, как первый абзац главы."""
    doc = Document(docx)
    paras = doc.paragraphs
    for prev, cur in zip(paras, paras[1:]):
        if prev.style.name == "Scene Break" and cur.style.name in ("Body Text", "Normal"):
            cur.style = doc.styles["First Paragraph"]
    doc.save(docx)


def build(lang: str):
    files = chapters(lang)
    if not files:
        print(f"[{lang}] глав нет, пропускаю")
        return
    out = ROOT / "build" / lang
    out.mkdir(parents=True, exist_ok=True)
    src = out / "book.md"
    src.write_text("\n\n".join(typography.clean(f.read_text(encoding="utf-8"), lang)
                               for f in files), encoding="utf-8")
    meta = ROOT / lang / "meta.yaml"
    fmt = "markdown-smart" if lang == "ru" else "markdown+smart"
    run = lambda *a: subprocess.run(["pandoc", "-f", fmt, *a], check=True)

    # docx: без титула и метаданных — площадки добавляют их сами.
    docx = out / "book.docx"
    heading_shift = ["--shift-heading-level-by=1"] if lang == "ru" else []
    run(str(src), "-o", str(docx), f"--reference-doc={TOOLS / f'ref-{lang}.docx'}",
        *heading_shift)
    fix_after_scene_breaks(docx)

    run(str(meta), str(src), "-o", str(out / "book.epub"),
        f"--css={TOOLS / 'book.css'}", "--split-level=1")
    if lang == "ru":
        run(str(meta), str(src), "-t", "fb2", "-o", str(out / "book.fb2"))
    print(f"[{lang}] {len(files)} гл. -> {out}")


if __name__ == "__main__":
    for lang in sys.argv[1:] or ["ru", "en"]:
        build(lang)
