"""Проверка стиля главы: python3 tools/check.py ru/01-*.md [en/01-*.md ...]

Ловит канцелярит, длинные предложения, маркеры «ИИ-языка», типографику,
а также повторы слов рядом, однотипное начало предложений, цепочки рубленых
фраз, абзацы-одностроки и лишние притяжательные местоимения.
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


REPEAT_WINDOW = 40  # слов: одно и то же слово ближе этого расстояния — повтор
CONTENT_POS = {"NOUN", "VERB", "INFN", "ADJF", "ADJS", "ADVB", "PRTF", "PRTS", "GRND",
               "NUMR", "COMP"}
SKIP_RU = {"быть", "весь", "это", "этот", "тот", "такой", "свой", "который", "сам",
           "самый", "так", "уже", "ещё", "только", "тоже", "очень", "сказать", "мочь"}
STOP_EN = set("""a an the and or but if then so of to in on at by for with from into onto
over under about as than that this these those it its it's he she they them her him his
their there here was were is are be been being had has have do did does not no nor
would could should will can may might must one ones what which who whom whose when where
why how all any some every each just very too also only said says say back up down out
off again still even ever more most much many such own same other another i you we me us
my your our mine yours""".split())

_morph = None


def lemma(word: str, lang: str):
    """(лемма, знаменательное ли слово)."""
    w = word.lower().strip("’'-")
    if lang == "en":
        if w in STOP_EN or len(w) < 3:
            return w, False
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        return w, True
    global _morph
    if _morph is None:
        try:
            import pymorphy3
            _morph = pymorphy3.MorphAnalyzer()
        except ImportError:
            _morph = False
    if not _morph:
        return w, len(w) > 3
    p = _morph.parse(w)[0]
    content = (p.tag.POS in CONTENT_POS or "Name" in p.tag) and "Apro" not in p.tag \
        and p.normal_form not in SKIP_RU
    return p.normal_form, content


def repetition_report(text: str, lang: str):
    """Повторы, однотипные начала, рубленые цепочки, одностроки, местоимения."""
    out = []
    tokens = []
    for n, line in enumerate(text.split("\n"), 1):
        if line.startswith("#"):
            continue
        for w in words(line):
            lem, content = lemma(w, lang)
            tokens.append((lem, content, n, w))
    last, reps = {}, {}
    for i, (lem, content, n, w) in enumerate(tokens):
        if content and lem in last and i - last[lem] <= REPEAT_WINDOW:
            reps.setdefault(n, []).append(w.lower())
        if content:
            last[lem] = i
    if reps:
        total = sum(len(v) for v in reps.values())
        out.append(f"\nПовторы рядом (ближе {REPEAT_WINDOW} слов): {total}")
        for n in sorted(reps):
            out.append(f"  стр. {n}: {', '.join(reps[n])}")

    dialog_marks = ("—", "-") if lang == "ru" else ("“", '"')
    narrative = [ln for ln in text.split("\n")
                 if ln.strip() and not ln.startswith("#") and not ln.lstrip().startswith(dialog_marks)
                 and not ln.strip().startswith("*")]
    starts, streak, stac, one_liners = [], [], [], []
    for ln in narrative:
        ss = sentences(ln)
        if len(ss) == 1 and len(words(ss[0])) <= 8:
            one_liners.append(ss[0])
        prev = None
        for s_ in ss:
            first = words(s_)[0].lower() if words(s_) else ""
            if first and first == prev:
                starts.append(s_[:70])
            prev = first
            if len(words(s_)) <= 5:
                streak.append(s_)
            else:
                if len(streak) >= 3:
                    stac.append(" ".join(streak))
                streak = []
        if len(streak) >= 3:
            stac.append(" ".join(streak))
        streak = []
    if starts:
        out.append(f"\nПредложения подряд с одного слова: {len(starts)}")
        out += [f"  {x}" for x in starts]
    if stac:
        out.append(f"\nЦепочки рубленых фраз (3+ подряд по ≤5 слов): {len(stac)}")
        out += [f"  {x[:120]}" for x in stac]
    if one_liners:
        out.append(f"\nАбзацы-одностроки (≤8 слов, не диалог): {len(one_liners)}")
        out += [f"  {x}" for x in one_liners]

    n_words = max(len(tokens), 1)
    if lang == "ru":
        poss = len(re.findall(r"(?<!\w)(?:её|его|их|сво[йеяиюём]\w*)(?!\w)", text, flags=re.I))
        comp = len(re.findall(r"(?<!\w)(?:словно|будто|точно|казалось)(?!\w)", text, flags=re.I))
        name = len(re.findall(r"Наташ\w*", text))
    else:
        poss = len(re.findall(r"\b(?:her|his|their)\b", text, flags=re.I))
        comp = len(re.findall(r"\bas if\b|\bas though\b|\blike a\b", text, flags=re.I))
        name = len(re.findall(r"\bNatalie\b", text))
    out.append(f"\nНа 1000 слов: имя героини {1000 * name / n_words:.0f}, "
               f"притяжательные местоимения {1000 * poss / n_words:.0f}, "
               f"сравнения-«будто» {1000 * comp / n_words:.0f}")
    return out


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
    print("\n".join(repetition_report(text, lang)))


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        report(Path(arg))
