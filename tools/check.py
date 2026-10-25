"""Проверка стиля главы: python3 tools/check.py ru/01-*.md [en/01-*.md ...]

Ловит канцелярит, длинные предложения, маркеры «ИИ-языка» и типографику.
Это подсказки, а не приговор: каждое срабатывание смотрим глазами.
"""
import re
import sys
from pathlib import Path

LONG = {"ru": 25, "en": 28}          # слов в предложении — уже тяжело
TARGET = {"ru": (9, 14), "en": (9, 13)}

KANCELYARIT = [
    r"\bявля(?:ет|ют)ся\b", r"\bосуществ\w+", r"\bпроизв(?:ести|одить|ёл|ел\w*)\b",
    r"\bданн(?:ый|ая|ое|ые|ого|ой|ом)\b", r"\bв связи с\b", r"\bс целью\b",
    r"\bв процессе\b", r"\bимеет место\b", r"\bв рамках\b", r"\bв качестве\b",
    r"\bпо причине\b", r"\bв течение\b", r"\bв результате\b", r"\bналичи\w+",
    r"\bотсутстви\w+", r"\bвышеуказанн\w+", r"\bнаходил(?:ся|ась|ось|ись)\b",
    r"\bсовершил[аи]?\b", r"\bпринял[аи]? решение\b", r"\bоказ(?:ал|ыва)\w* влияние\b",
    r"\bв данный момент\b", r"\bна сегодняшний день\b", r"\bв то время как\b",
    r"\b\w+(?:ние|ния|нием|нии)\s+\w+(?:ния|ний|нию)\b",  # цепочки отглагольных
    r"\bкоторый\b.{0,60}\bкоторый\b",                    # «который» на «который»
]

AI_RU = [
    r"погрузи\w*", r"не просто\b.{0,40}\bа\b", r"\bв мире,? где\b", r"стоит отметить",
    r"важно понимать", r"ключев\w+ рол\w+", r"\bуникальн\w+", r"невидим\w+ нит\w+",
    r"тих\w+ шёпот\w*", r"эхом отозвал\w+", r"что-то внутри\b", r"сердце пропустило",
    r"ком в горле", r"мурашки\b", r"затаив дыхание", r"запах озона", r"пылинк\w+",
    r"смес\w+ (?:страха|надежды|облегчения)", r"ещё не знал\w*", r"словно сама",
    r"\bЭлар\w*|\bЛир[аыеу]\b|\bКаэл\w*", r"оставляя после себя", r"\bвихр\w+ эмоций",
    r"это был[аио]? не\b.{0,30}\bа\b",
]
AI_EN = [
    r"\bdelv\w+", r"\btapestry\b", r"\btestament\b", r"\bunderscore\w*", r"\bvibrant\b",
    r"\bintricate\b", r"\bpivotal\b", r"breath (?:she|he|they) didn'?t know",
    r"barely above a whisper", r"shivers? down", r"jaw tighten\w*", r"\ba flicker of\b",
    r"something shifted", r"the air (?:was )?thick with", r"\bozone\b", r"\bElara\b|\bLyra\b|\bKael\b",
    r"\bit wasn'?t\b.{0,40}\bit was\b", r"\bnot just\b.{0,30}\bbut\b", r"\bshimmer\w*",
    r"\bunbeknownst\b", r"little did (?:she|he|they) know", r"a mix(?:ture)? of (?:fear|relief|hope)",
]
TYPO = {
    "ru": [(r'"', "прямые кавычки — нужны «ёлочки»"),
           (r"(?:^|\s)-\s", "дефис вместо тире"),
           (r"\.\.\.", "три точки — нужен знак …"),
           (r"[“”]", "английские кавычки в русском тексте")],
    "en": [(r" — |\s--\s", "em dash with spaces (Chicago: no spaces)"),
           (r"[«»]", "Russian guillemets in English text")],
}


def sentences(text: str):
    text = re.sub(r"^#.*$|^\s*(\*\s*){3}$", "", text, flags=re.M)
    text = re.sub(r"[*_]", "", text)
    parts = re.split(r"(?<=[.!?…])[»”\"]?\s+(?=[—\-«“\"A-ZА-ЯЁ])", text)
    return [p.strip() for p in parts if re.search(r"\w", p)]


def words(s: str):
    return re.findall(r"[\w’'-]+", s)


def report(path: Path):
    lang = "en" if path.parts[-2] == "en" else "ru"
    text = path.read_text(encoding="utf-8")
    paras = [p for p in text.split("\n") if p.strip() and not p.startswith("#")]
    sents = sentences(text)
    lens = [len(words(s)) for s in sents]
    total = sum(lens) or 1
    dialog_marks = ("—", "-") if lang == "ru" else ("“", '"')
    dialog = sum(len(words(p)) for p in paras if p.lstrip().startswith(dialog_marks))

    print(f"\n=== {path} ===")
    lo, hi = TARGET[lang]
    avg = total / max(len(lens), 1)
    print(f"Слов: {total}  Предложений: {len(lens)}  Средняя длина: {avg:.1f} "
          f"(ориентир {lo}–{hi})  Диалог: {100 * dialog / total:.0f}% (ориентир 30–45%)")

    long_ = [(n, s) for n, s in zip(lens, sents) if n > LONG[lang]]
    if long_:
        print(f"\nДлинные предложения (>{LONG[lang]} слов): {len(long_)}")
        for n, s in long_:
            print(f"  [{n}] {s[:140]}{'…' if len(s) > 140 else ''}")

    def hits(patterns, title):
        found = []
        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.I | re.M):
                line = text.count("\n", 0, m.start()) + 1
                found.append((line, m.group(0)))
        if found:
            print(f"\n{title}: {len(found)}")
            for line, w in sorted(found):
                print(f"  стр. {line}: {w}")

    if lang == "ru":
        hits(KANCELYARIT, "Канцелярит")
    hits(AI_RU if lang == "ru" else AI_EN, "Маркеры ИИ-языка")
    hits([p for p, _ in TYPO[lang]], "Типографика (build.py исправит сам)")

    dashes = text.count("—")
    if lang == "en" and dashes > total / 150:
        print(f"\nМного длинных тире: {dashes} на {total} слов — проверить, не ИИ-ритм ли")
    para_lens = [len(words(p)) for p in paras if not p.lstrip().startswith(dialog_marks)]
    if len(para_lens) > 5 and max(para_lens) - min(para_lens) < 25:
        print("\nАбзацы почти одной длины — ритм монотонный")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        report(Path(arg))
