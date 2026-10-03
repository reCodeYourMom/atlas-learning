"""Tests errata E8 — détection des tokens latins résiduels dans les stems AR.

Le check numérique (ar_math_preserved) ne peut pas attraper un mot anglais non
traduit (« ONE ») : ar_latin_tokens complète le gate G3.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.items.arabic import (
    ar_content_latin_tokens,
    ar_content_suspect_glyphs,
    ar_latin_tokens,
    ar_math_preserved,
    ar_suspect_glyphs,
)


def test_detects_untranslated_english_word():
    # le cas réel trouvé en banque (errata E8)
    assert ar_latin_tokens("مربع يُقطع إلى 4 أجزاء متساوية. ما هو الجزء الذي يُمثّل ONE جزء؟") == ["ONE"]


def test_detects_broken_latex_markup():
    assert ar_latin_tokens("أي أكبر بين <frac{1}{4}> أو <frac{3}{4}>؟") == ["frac"]
    # \f de \frac avalé en form feed → 'rac' résiduel
    assert ar_latin_tokens("ما هو أقل مضاعف مشترك ل\x0crac{1}{3} و\x0crac{1}{8}؟") == ["rac"]


def test_no_false_positive_on_accepted_math_notation():
    # nombres, fractions, opérateurs, chiffres arabes-orientaux : aucune lettre → rien
    assert ar_latin_tokens("1/8 + 3/8 = ؟") == []
    assert ar_latin_tokens("٣/٤ × 12 = ؟") == []
    assert ar_latin_tokens("0.5 > 0.45") == []
    assert ar_latin_tokens("ما ناتج 2/5 + 4/5؟") == []


def test_single_latin_letter_tolerated():
    # une lettre isolée (variable) n'est pas un mot non traduit
    assert ar_latin_tokens("أوجد قيمة x في x/4 = 2") == []


def test_deduplicated_in_order_of_appearance():
    assert ar_latin_tokens("frac ثم They are They equal frac") == ["frac", "They", "are", "equal"]


def test_empty_and_none_are_safe():
    assert ar_latin_tokens("") == []
    assert ar_latin_tokens(None) == []


def test_content_level_scan_covers_stem_options_answer():
    content = {
        "stem": "أي أكبر بين 1/4 أو 3/4؟",
        "options": ["3/5", "3/4", "1/4", "They are equal"],
        "answer": "3/4",
    }
    assert ar_content_latin_tokens(content) == ["They", "are", "equal"]
    assert ar_content_latin_tokens(None) == []
    # contenu corrigé : plus aucun token
    content["options"][3] = "هما متساويان"
    assert ar_content_latin_tokens(content) == []



# --- Revue 2026-07-12 : glyphes parasites non latins + faux positifs du check numérique ---


def test_suspect_glyphs_detects_encoding_corruption():
    # cas réels trouvés en banque : nombres remplacés par des glyphes grecs/combinants
    assert ar_suspect_glyphs("أي أكبر بين ±̆ أو ±̄؟") == ["±", "\u0306", "\u0304"]
    assert ar_suspect_glyphs("تحويل 2πα إلى كسر غير صحيح.") == ["π", "α"]
    assert ar_suspect_glyphs("مقارنة بـ ±Ⓒ، الكسر ⅒⅖ هو…") == ["±", "Ⓒ", "⅒", "⅖"]


def test_suspect_glyphs_clean_arabic_content_passes():
    # arabe scolaire légitime : diacritiques arabes, chiffres 0-9, fractions ASCII, ponctuation
    assert ar_suspect_glyphs("دائرة تُقْطَع إلى ثمانية أجزاء متساوية. ما الجزء الذي يمثّل 1/2؟") == []
    assert ar_suspect_glyphs("ما هو ناتج 3.5 × 2 ؟ «اختر الإجابة»") == []
    assert ar_suspect_glyphs(None) == []


def test_content_suspect_glyphs_covers_all_fields():
    content = {"stem": "سليم", "options": ["1/2", "±̆"], "answer": "πα"}
    assert ar_content_suspect_glyphs(content) == ["±", "\u0306", "π", "α"]
    assert ar_content_suspect_glyphs(None) == []


def test_math_preserved_translated_textual_option_not_flagged():
    # revue 2026-07-12 : 29 faux positifs — une option textuelle traduite ne doit pas recaler
    en = {"stem": "Compare 1/2 and 2/4.", "options": ["1/2", "2/4", "They are equal"],
          "answer": "They are equal"}
    ar = {"stem": "قارن بين 1/2 و 2/4.", "options": ["1/2", "2/4", "هما متساويان"],
          "answer": "هما متساويان"}
    assert ar_math_preserved(en, ar) is True


def test_math_preserved_still_catches_glyph_replaced_numbers():
    en = {"stem": "x", "options": ["1/2", "1/6"], "answer": "1/2"}
    ar = {"stem": "س", "options": ["±̆", "±̄"], "answer": "±̆"}
    assert ar_math_preserved(en, ar) is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  PASS {fn.__name__}")
    print(f"\n{len(fns)} tests OK")
