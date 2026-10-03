"""Traduction arabe DÉTERMINISTE de la banque (pendant de items/arabic.py, sans LLM).

Pourquoi ce module existe
-------------------------
`items/arabic.py` fait traduire les items par un modèle (ALLaM/Groq) : c'est la voie
normale pour du contenu rédigé. Mais la banque déterministe (items/deterministic.py) n'est
PAS du contenu rédigé : ses 300 items sortent de ~37 gabarits d'énoncé, et leurs options
sont des fractions pures, sans un mot à traduire. Les faire passer par un LLM revenait à
mettre une clé d'API et un appel réseau sur le chemin critique de la démo — pour traduire
37 phrases connues d'avance.

Conséquence directe, mesurée : sans `content_ar`, `review.promote_to_active` refuse de
promouvoir (le gate `ar_validated`), donc AUCUN item actif, donc pas de session adaptative
ni de remédiation. L'arabe n'était pas un confort : c'était le verrou de la banque servie.

Contrat
-------
- Les nombres, fractions et symboles mathématiques sont recopiés à l'identique (chiffres
  arabes d'Orient volontairement écartés : `ar_math_preserved` compare les tokens numériques
  EN↔AR, et l'élève lit les mêmes chiffres que dans son manuel bilingue).
- `translate_content` renvoie None si l'énoncé ne correspond à AUCUN gabarit connu — on ne
  devine jamais. Le script appelant compte les non-couverts et un test verrouille les 300.
- Arabe standard moderne (الفصحى), registre scolaire.
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional, Pattern, Tuple

# Options non numériques : les seules de toute la banque (4 valeurs).
_OPTIONS_AR = {
    "They are equal": "متساويان",
    "equal to": "يساويه",
    "greater than": "أكبر منه",
    "less than": "أصغر منه",
}

# Formes géométriques citées par les énoncés visuels.
_SHAPES_AR = {
    "circle": "دائرة",
    "rectangle": "مستطيل",
    "square": "مربّع",
    "pizza": "بيتزا",
    "bar": "شريط",
}

def _counted(n, plural: str, singular: str) -> str:
    """Accord du nom compté (تمييز العدد) écrit avec un CHIFFRE : 3-10 → pluriel,
    11+ → مفرد منصوب (« 12 جزءًا متساويًا », et non « 12 أجزاء »).

    Le duel (« جزأين ») est volontairement écarté : il ferait disparaître le chiffre 2 de
    l'énoncé, or `ar_stem_numbers_preserved` exige que l'arabe reprenne TOUS les nombres de
    l'anglais. Cet invariant protège contre le vrai risque — un item AR qui pose un problème
    mathématique différent de son EN — et prime sur le raffinement grammatical.
    """
    k = int(n)
    return f"{k} {plural}" if k <= 10 else f"{k} {singular}"


def _parts(n) -> str:
    return _counted(n, "أجزاء متساوية", "جزءًا متساويًا")


def _intervals(n) -> str:
    return _counted(n, "فترات متساوية", "فترةً متساويةً")


# (gabarit EN compilé, fabricant de l'énoncé AR à partir des groupes capturés).
# L'ordre compte : le premier gabarit qui matche gagne, donc les variantes les plus
# spécifiques (« … ? (mixed number, simplest form) ») viennent AVANT les plus générales.
_RULES: List[Tuple[Pattern, Callable[..., str]]] = []


def _rule(pattern: str):
    def deco(fn):
        _RULES.append((re.compile(pattern + r"\s*$"), fn))
        return fn
    return deco


# ---------- fractions unitaires & partage ----------

@_rule(r"A (circle|rectangle|square|pizza) is cut into (\d+) equal parts\. "
       r"What fraction is ONE part\?")
def _cut_shape(shape, n):
    return (f"قُسِّمت {_SHAPES_AR[shape]} إلى {_parts(n)}. "
            "ما الكسر الذي يمثّل جزءًا واحدًا؟")


@_rule(r"A whole is split into (\d+) equal parts\. What fraction is ONE part\?")
def _split_whole(n):
    return f"قُسِّم كلٌّ إلى {_parts(n)}. ما الكسر الذي يمثّل جزءًا واحدًا؟"


@_rule(r"A bar is divided into (\d+) equal parts and (\d+) parts? (?:are|is) shaded\. "
       r"What fraction is shaded\?")
def _bar_shaded(d, n):
    return f"قُسِّم شريط إلى {_parts(d)}، وظُلِّل {n} منها. ما الكسر المُظلَّل؟"


@_rule(r"A whole is divided into (\d+) equal parts and (\d+) parts? (?:are|is) taken\. "
       r"What fraction is taken\?")
def _whole_taken(d, n):
    return f"قُسِّم كلٌّ إلى {_parts(d)}، وأُخِذ منها {n}. ما الكسر المأخوذ؟"


@_rule(r"Express 1 whole as a fraction with denominator (\d+)\.")
def _whole_as_fraction(d):
    return f"اكتب 1 صحيحًا على صورة كسر مقامه {d}."


# ---------- demi / quart ----------

@_rule(r"Which fraction means one half\?")
def _one_half():
    return "أيّ كسر يعني نصفًا واحدًا؟"


@_rule(r"Which fraction means one quarter\?")
def _one_quarter():
    return "أيّ كسر يعني رُبعًا واحدًا؟"


@_rule(r"Two quarters make which fraction\?")
def _two_quarters():
    return "رُبعان يساويان أيّ كسر؟"


@_rule(r"How many quarters make one whole\?")
def _how_many_quarters():
    return "كم رُبعًا يُكوّن واحدًا صحيحًا؟"


@_rule(r"How many halves make one whole\?")
def _how_many_halves():
    return "كم نصفًا يُكوّن واحدًا صحيحًا؟"


# ---------- droite graduée, ensembles, équivalence ----------

@_rule(r"A number line from 0 to 1 is split into (\d+) equal intervals\. "
       r"What fraction is at the (\d+)(?:st|nd|rd|th) tick after 0\?")
def _number_line(d, k):
    return (f"خطّ أعداد من 0 إلى 1 مقسوم إلى {_intervals(d)}. "
            f"ما الكسر عند العلامة رقم {k} بعد 0؟")


@_rule(r"A set has (\d+) objects\. (\d+/\d+) of them are red\. How many are red\?")
def _set_of(n, f):
    return f"مجموعة فيها {n} عنصرًا، {f} منها حمراء. كم عددُ العناصر الحمراء؟"


@_rule(r"A model shows (\d+/\d+) shaded\. Which fraction is equivalent \(same amount\)\?")
def _equiv_visual(f):
    return f"نموذج يُظهر {f} مُظلَّلًا. أيّ كسر يكافئه (المقدار نفسه)؟"


@_rule(r"Find the missing numerator: (\d+/\d+) = x/(\d+)")
def _missing_numerator(f, d):
    return f"أوجد البسط المجهول: {f} = x/{d}"


@_rule(r"Write (\d+/\d+) in lowest terms\.")
def _lowest_terms(f):
    return f"اكتب {f} بأبسط صورة."


# ---------- comparaison ----------

@_rule(r"Which is greater: (\d+/\d+) or (\d+/\d+)\?")
def _which_greater(a, b):
    return f"أيّهما أكبر: {a} أم {b}؟"


@_rule(r"Compared to 1/2, the fraction (\d+/\d+) is…")
def _benchmark(f):
    return f"بالمقارنة مع 1/2، فإنّ الكسر {f} …"


# ---------- arithmétique entière ----------

@_rule(r"What is (\d+) × (\d+)\?")
def _mult(a, b):
    return f"ما ناتج {a} × {b}؟"


@_rule(r"Which number is a factor of (\d+)\?")
def _factor(n):
    return f"أيّ عدد ممّا يلي عاملٌ للعدد {n}؟"


@_rule(r"What is the greatest common divisor of (\d+) and (\d+)\?")
def _gcd(a, b):
    return f"ما القاسم المشترك الأكبر للعددين {a} و{b}؟"


@_rule(r"What is the least common multiple of (\d+) and (\d+)\?")
def _lcm(a, b):
    return f"ما المضاعف المشترك الأصغر للعددين {a} و{b}؟"


@_rule(r"What is the least common denominator for (\d+/\d+) and (\d+/\d+)\?")
def _lcd(a, b):
    return f"ما أصغر مقام مشترك للكسرين {a} و{b}؟"


# ---------- addition / soustraction de fractions ----------
# Variantes qualifiées d'abord (le premier gabarit qui matche gagne).

@_rule(r"What is ([\d ]+/\d+) \+ ([\d ]+/\d+)\? \(mixed number, simplest form\)")
def _add_mixed_simplest(a, b):
    return f"ما ناتج {a} + {b}؟ (اكتبه عددًا كسريًّا بأبسط صورة)"


@_rule(r"What is ([\d ]+/\d+) \+ ([\d ]+/\d+)\? \(mixed number\)")
def _add_mixed(a, b):
    return f"ما ناتج {a} + {b}؟ (اكتبه عددًا كسريًّا)"


@_rule(r"What is (\d+/\d+) \+ (\d+/\d+)\? \(give simplest form\)")
def _add_simplest(a, b):
    return f"ما ناتج {a} + {b}؟ (اكتبه بأبسط صورة)"


@_rule(r"What is (\d+/\d+) − (\d+/\d+)\? \(simplest form\)")
def _sub_simplest(a, b):
    return f"ما ناتج {a} − {b}؟ (اكتبه بأبسط صورة)"


@_rule(r"What is (\d+/\d+) \+ (\d+/\d+)\?")
def _add(a, b):
    return f"ما ناتج {a} + {b}؟"


@_rule(r"What is (\d+/\d+) − (\d+/\d+)\?")
def _sub(a, b):
    return f"ما ناتج {a} − {b}؟"


@_rule(r"Add \(give a mixed number\): (\d+/\d+) \+ (\d+/\d+)")
def _add_give_mixed(a, b):
    return f"اجمع واكتب الناتج عددًا كسريًّا: {a} + {b}"


@_rule(r"Add and simplify: (\d+/\d+) \+ (\d+/\d+)")
def _add_simplify(a, b):
    return f"اجمع وبسّط: {a} + {b}"


@_rule(r"Subtract and simplify: (\d+/\d+) − (\d+/\d+)")
def _sub_simplify(a, b):
    return f"اطرح وبسّط: {a} − {b}"


# ---------- conversions ----------

@_rule(r"Convert (\d+/\d+) to a mixed number\.")
def _to_mixed(f):
    return f"حوّل {f} إلى عدد كسريّ."


@_rule(r"Convert (\d+ \d+/\d+) to an improper fraction\.")
def _to_improper(m):
    return f"حوّل {m} إلى كسر غير حقيقيّ."


# =========================== API publique ===========================


def translate_stem(stem_en: str) -> Optional[str]:
    """Énoncé arabe correspondant, ou None si aucun gabarit ne matche (jamais de devinette)."""
    if not stem_en:
        return None
    text = stem_en.strip()
    for pattern, build in _RULES:
        m = pattern.match(text)
        if m:
            return build(*m.groups())
    return None


def translate_option(option: str) -> str:
    """Option arabe. Les options numériques (l'écrasante majorité) sont recopiées telles quelles."""
    return _OPTIONS_AR.get(str(option).strip(), str(option))


def translate_content(content_en: Optional[dict]) -> Optional[dict]:
    """Traduit un `ItemContent` complet. None si l'énoncé n'est pas couvert.

    `answer` est traduit par la MÊME fonction que les options : la clé de correction reste
    donc égale à l'option correspondante côté arabe — invariant sur lequel repose
    `session_service.grade_answer` quand la session est servie en AR.
    """
    if not content_en:
        return None
    stem_ar = translate_stem(content_en.get("stem", ""))
    if stem_ar is None:
        return None
    out = {"stem": stem_ar}
    if content_en.get("options") is not None:
        out["options"] = [translate_option(o) for o in content_en["options"]]
    if content_en.get("answer") is not None:
        out["answer"] = translate_option(content_en["answer"])
    return out
