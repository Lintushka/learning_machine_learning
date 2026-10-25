"""Типографская чистка исходников перед сборкой (и проверка в check.py)."""
import re

NBSP = " "
SCENE_RE = re.compile(r"^\s*(\*\s*){3}\s*$")


def _ru_quotes(line: str) -> str:
    """Прямые кавычки -> «ёлочки», вложенные -> „лапки“."""
    out, depth = [], 0
    for i, ch in enumerate(line):
        if ch != '"':
            out.append(ch)
            continue
        prev = line[i - 1] if i else " "
        opening = prev.isspace() or prev in "([{—-«„/"
        if opening:
            out.append("«" if depth == 0 else "„")
            depth += 1
        else:
            depth = max(depth - 1, 0)
            out.append("»" if depth == 0 else "“")
    return "".join(out)


def ru(line: str) -> str:
    if SCENE_RE.match(line) or line.startswith("#"):
        return line
    line = _ru_quotes(line)
    line = line.replace("...", "…")
    # Реплика в начале абзаца: "- ", "-- ", "– " -> "— " с неразрывным пробелом.
    line = re.sub(r"^(\s*)(?:--|-|–|—)[  ]+", rf"\1—{NBSP}", line)
    # Тире между словами: неразрывный пробел перед, обычный после.
    line = re.sub(r"[  ]+(?:--|-|–|—)[  ]+", f"{NBSP}— ", line)
    return line


def en(line: str) -> str:
    if SCENE_RE.match(line) or line.startswith("#"):
        return line
    # Chicago: длинное тире без пробелов. Кавычки и ... доделает pandoc (smart).
    line = re.sub(r"[  ]+(?:--|—)[  ]+", "—", line)
    line = re.sub(r"(?<=\w)--(?=\w)", "—", line)
    line = line.replace("...", "…")
    return line


def scene_break(lang: str) -> str:
    mark = r"\*\*\*" if lang == "ru" else r"\* \* \*"
    return f'::: {{custom-style="Scene Break"}}\n{mark}\n:::'


def clean(text: str, lang: str) -> str:
    fix = ru if lang == "ru" else en
    lines = []
    for line in text.splitlines():
        lines.append(scene_break(lang) if SCENE_RE.match(line) else fix(line))
    return "\n".join(lines) + "\n"
