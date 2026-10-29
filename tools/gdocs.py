"""Зеркало глав в Google Docs.

  python3 tools/gdocs.py text ru            -> текст для insertText (JSON-строка)
  python3 tools/gdocs.py style ru DOC.json  -> запросы оформления по свежему read_doc

ID документов лежат в tools/gdocs.json. Текст берётся из всех глав языка,
прошедших ту же типографскую чистку, что и сборка (build.py).
"""
import json
import subprocess
import sys
from pathlib import Path

import typography

ROOT = Path(__file__).resolve().parent.parent
FIRST_LINE_PT = 35.43  # абзацный отступ ≈ 1,25 см


def paragraphs(lang: str):
    """[(kind, text, italic_spans)] — kind: heading | scene | first | body."""
    files = sorted((ROOT / lang).glob("[0-9]*.md"))
    md = "\n\n".join(typography.clean(f.read_text(encoding="utf-8"), lang) for f in files)
    fmt = "markdown-smart" if lang == "ru" else "markdown+smart"
    ast = json.loads(subprocess.run(["pandoc", "-f", fmt, "-t", "json"], input=md,
                                    capture_output=True, text=True, check=True).stdout)

    def inline(nodes, out, spans, italic=False):
        for n in nodes:
            t, c = n["t"], n.get("c")
            if t == "Str":
                start = len(out[0])
                out[0] += c
                if italic:
                    spans.append((start, len(out[0])))
            elif t in ("Space", "SoftBreak"):
                out[0] += " "
                if italic:
                    spans.append((len(out[0]) - 1, len(out[0])))
            elif t == "Emph":
                inline(c, out, spans, True)
            elif t == "Quoted":
                q = ("“", "”") if c[0]["t"] == "DoubleQuote" else ("‘", "’")
                out[0] += q[0]
                inline(c[1], out, spans, italic)
                out[0] += q[1]
            else:
                raise ValueError(f"не умею {t}")

    result, prev = [], "heading"
    for block in ast["blocks"]:
        t, c = block["t"], block["c"]
        out, spans = [""], []
        if t == "Header":
            inline(c[2], out, spans)
            kind = "heading"
        elif t == "Div":
            inline(c[1][0]["c"], out, spans)
            kind = "scene"
        elif t == "Para":
            inline(c, out, spans)
            kind = "first" if prev in ("heading", "scene") else "body"
        else:
            raise ValueError(f"не умею блок {t}")
        result.append((kind, out[0], merge(spans)))
        prev = kind
    return result


def merge(spans):
    merged = []
    for s, e in spans:
        if merged and merged[-1][1] == s:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def u16(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def text(lang: str) -> str:
    return "\n".join(p[1] for p in paragraphs(lang))


def style(lang: str, doc_path: str):
    doc = json.loads(Path(doc_path).read_text(encoding="utf-8"))
    doc = doc.get("content", doc)
    tab = doc["tabs"][0]
    content = [e for e in tab["documentTab"]["body"]["content"] if "paragraph" in e]
    paras = paragraphs(lang)
    assert len(content) == len(paras), (len(content), len(paras))
    tab_id = tab["tabProperties"]["tabId"]
    reqs = []
    whole = {"startIndex": content[0]["startIndex"], "endIndex": content[-1]["endIndex"] - 1,
             "tabId": tab_id}

    def para_style(rng, kind):
        ps = {"namedStyleType": "HEADING_1" if kind == "heading" else "NORMAL_TEXT",
              "alignment": "CENTER" if kind in ("heading", "scene") else "JUSTIFIED",
              "indentFirstLine": {"magnitude": FIRST_LINE_PT if kind == "body" else 0,
                                  "unit": "PT"},
              "indentStart": {"magnitude": 0, "unit": "PT"},
              "indentEnd": {"magnitude": 0, "unit": "PT"},
              "spaceAbove": {"magnitude": 12 if kind == "scene" else 0, "unit": "PT"},
              "spaceBelow": {"magnitude": 12 if kind in ("scene", "heading") else 0,
                             "unit": "PT"}}
        return {"updateParagraphStyle": {
            "range": rng, "paragraphStyle": ps,
            "fields": "namedStyleType,alignment,indentFirstLine,indentStart,indentEnd,"
                      "spaceAbove,spaceBelow"}}

    # Сначала весь текст как обычные абзацы, потом исключения.
    reqs.append({"updateTextStyle": {"range": whole, "textStyle": {},
                                     "fields": "bold,italic,underline"}})
    reqs.append(para_style(whole, "body"))
    italic = []
    for el, (kind, ptext, spans) in zip(content, paras):
        got = "".join(r["textRun"]["content"] for r in el["paragraph"]["elements"]
                      if "textRun" in r).rstrip("\n")
        assert got == ptext, f"расхождение:\n{got[:80]}\n{ptext[:80]}"
        s, e = el["startIndex"], el["endIndex"]
        if kind != "body":
            reqs.append(para_style({"startIndex": s, "endIndex": e, "tabId": tab_id}, kind))
        for a, b in spans:
            rng = [s + u16(ptext[:a]), s + u16(ptext[:b])]
            if italic and rng[0] - italic[-1][1] <= 1:  # соседние курсивные абзацы
                italic[-1][1] = rng[1]
            else:
                italic.append(rng)
    for a, b in italic:
        reqs.append({"updateTextStyle": {
            "range": {"startIndex": a, "endIndex": b, "tabId": tab_id},
            "textStyle": {"italic": True}, "fields": "italic"}})
    return {"requests": reqs, "writeControl": {"requiredRevisionId": doc["revisionId"]}}


if __name__ == "__main__":
    cmd, lang = sys.argv[1], sys.argv[2]
    if cmd == "text":
        print(json.dumps(text(lang), ensure_ascii=False).replace(" ", "\\u00a0"))
    elif cmd == "style":
        print(json.dumps(style(lang, sys.argv[3]), ensure_ascii=False))
