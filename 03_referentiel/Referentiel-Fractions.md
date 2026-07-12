# Référentiel Fractions — Table de travail (FIGÉ MVP)

**Statut** : Figé · **Date** : 2026-06-20 · Vertical MVP Atlas Learning

Validé : DAG sans cycle · 32 nœuds · 35 arêtes HARD / 11 SOFT · profondeur 12 · 2 racines.

Corrections appliquées : PPCM rerouté via COMMON_DENOM (LCM→COMMON_DENOM 0.85) ; ajout IMPROPER_TO_MIXED→ADD_UNLIKE_FULL (HARD 0.72).

Poids = `correlation_strength` expert initial (weight_source=expert, version=1). À ré-estimer sur trafic.

| # | Code | Compétence (EN) | Grade | Prior | Prérequis HARD (poids) | Prérequis SOFT (poids) | Contextes d'items |
|---|------|-----------------|-------|-------|------------------------|------------------------|-------------------|
| 1 | `NS.EQUAL_SHARES` | Partition shapes into equal shares | G2 | 1150 | — | — | 2 parts, 3 parts, 4 parts… |
| 2 | `NS.HALVES_QUARTERS` | Identify halves and quarters | G2 | 1200 | NS.EQUAL_SHARES (0.85) | — | half, quarter, third… |
| 3 | `NS.NAME_FRACTION_VISUAL` | Name the fraction shown by a shaded model | G2 | 1280 | NS.HALVES_QUARTERS (0.8) | — | denominator<=4, denominator<=6, bar model… |
| 4 | `NF.ADD_SAME_NOSIMP` | Add fractions, same denominator, no simplifying | G3 | 1480 | NF.FRACTION_AS_PART (0.74) | — | proper result, denominator<=10, result<1 |
| 5 | `NF.COMPARE_SAME_DENOM` | Compare fractions with same denominator | G3 | 1500 | NF.FRACTION_AS_PART (0.76) | — | denominator<=8, < and >, ordering 3 fractions |
| 6 | `NF.COMPARE_SAME_NUM` | Compare fractions with same numerator | G3 | 1540 | NF.UNIT_FRACTION (0.7) | — | numerator=1, numerator<=3, reasoning about size |
| 7 | `NF.EQUIVALENCE_VISUAL` | Recognize equivalent fractions with models | G3 | 1520 | NF.FRACTION_AS_PART (0.8) | NF.NUMBER_LINE_PLACE (0.55) | 1/2=2/4, bar model, number line… |
| 8 | `NF.FRACTION_AS_PART` | Represent a fraction a/b of a whole | G3 | 1400 | NF.UNIT_FRACTION (0.88) | — | proper only, a<b, bar model… |
| 9 | `NF.FRACTION_OF_SET` | Find a fraction of a set of objects | G3 | 1450 | NF.FRACTION_AS_PART (0.75) | — | set<=12, unit fraction, non-unit fraction |
| 10 | `NF.NUMBER_LINE_PLACE` | Place a fraction on a number line | G3 | 1480 | NF.FRACTION_AS_PART (0.72) | — | 0 to 1, denominator<=8, ticks given… |
| 11 | `NF.SUB_SAME_NOSIMP` | Subtract fractions, same denominator, no simplifying | G3 | 1500 | — | NF.ADD_SAME_NOSIMP (0.65) | proper result, denominator<=10, no borrowing |
| 12 | `NF.UNIT_FRACTION` | Understand a unit fraction 1/b | G3 | 1350 | NS.NAME_FRACTION_VISUAL (0.82) | — | b<=6, b<=10, area model… |
| 13 | `NF.WHOLE_AS_FRACTION` | Recognize whole numbers as fractions (b/b=1) | G3 | 1430 | — | NF.UNIT_FRACTION (0.6) | b/b=1, a/1=a, number line |
| 14 | `NS.MULT_FACTS` | Recall multiplication facts to 100 | G3 | 1320 | — | — | x2 x3 x4, x5 x6, mixed up to 10 |
| 15 | `NF.ADD_SAME_IMPROPER` | Add fractions, same denominator, improper result | G4 | 1660 | NF.IMPROPER_TO_MIXED (0.7) | NF.ADD_SAME_SIMPLIFY (0.6) | result>1, convert to mixed, denominator<=12 |
| 16 | `NF.ADD_SAME_SIMPLIFY` | Add fractions, same denominator, simplify result | G4 | 1600 | NF.ADD_SAME_NOSIMP (0.8)<br>NF.SIMPLIFY_FRACTION (0.78) | — | result simplifiable, result=whole, denominator<=12 |
| 17 | `NF.ADD_UNLIKE_LCM` | Add fractions, unlike denom, requiring LCM | G4 | 1850 | NF.ADD_UNLIKE_SIMPLE (0.83)<br>NF.COMMON_DENOM (0.85) | — | coprime denoms, LCM needed, result proper |
| 18 | `NF.ADD_UNLIKE_SIMPLE` | Add fractions, unlike denom, one is multiple of other | G4 | 1760 | NF.ADD_SAME_NOSIMP (0.72)<br>NF.EQUIVALENCE_COMPUTE (0.82) | — | denom multiple, no simplify result, denominator<=12 |
| 19 | `NF.COMMON_DENOM` | Find a common denominator for two fractions | G4 | 1700 | NS.LCM (0.85)<br>NF.EQUIVALENCE_COMPUTE (0.8) | — | one is multiple of other, need LCM, denominator<=12 |
| 20 | `NF.COMPARE_BENCHMARK` | Compare fractions using benchmarks (1/2, 1) | G4 | 1640 | — | NF.COMPARE_SAME_DENOM (0.55) | benchmark 1/2, benchmark 1, mixed cases |
| 21 | `NF.COMPARE_DIFF_DENOM` | Compare fractions with different denominators | G4 | 1720 | NF.EQUIVALENCE_COMPUTE (0.84) | NF.COMPARE_BENCHMARK (0.58) | via equivalence, via cross-multiply, denominator<=12 |
| 22 | `NF.EQUIVALENCE_COMPUTE` | Generate equivalent fractions by multiplication | G4 | 1620 | NF.EQUIVALENCE_VISUAL (0.82) | NS.MULT_FACTS (0.58) | multiply num+den, factor<=5, find missing numerator |
| 23 | `NF.SIMPLIFY_FRACTION` | Simplify a fraction to lowest terms | G4 | 1700 | NF.EQUIVALENCE_COMPUTE (0.78) | NS.GCD (0.62) | common factor<=5, gcd needed, already simplified (trap) |
| 24 | `NF.SUB_SAME_SIMPLIFY` | Subtract fractions, same denominator, simplify result | G4 | 1620 | NF.SUB_SAME_NOSIMP (0.8)<br>NF.SIMPLIFY_FRACTION (0.76) | — | result simplifiable, denominator<=12 |
| 25 | `NS.FACTORS` | Find factors of a number | G4 | 1500 | NS.MULT_FACTS (0.74) | — | n<=24, n<=50, common factors |
| 26 | `NS.GCD` | Find greatest common divisor | G4 | 1660 | NS.FACTORS (0.75) | — | pair<=24, coprime (gcd=1), one divides other |
| 27 | `NS.LCM` | Find least common multiple | G4 | 1640 | NS.FACTORS (0.72) | — | pair<=12, one multiple of other, coprime pair |
| 28 | `NF.ADD_MIXED` | Add mixed numbers | G5 | 1980 | NF.MIXED_TO_IMPROPER (0.8)<br>NF.ADD_UNLIKE_FULL (0.82) | — | like denom, unlike denom, carry to whole |
| 29 | `NF.ADD_UNLIKE_FULL` | Add fractions, unlike denom, with simplify + improper | G5 | 1950 | NF.ADD_UNLIKE_LCM (0.84)<br>NF.SIMPLIFY_FRACTION (0.74)<br>NF.IMPROPER_TO_MIXED (0.72) | NF.ADD_SAME_IMPROPER (0.62) | simplify result, improper->mixed, denominator<=20 |
| 30 | `NF.IMPROPER_TO_MIXED` | Convert improper fraction to mixed number | G5 | 1820 | — | NF.MIXED_TO_IMPROPER (0.68) | result whole+fraction, simplify fraction part |
| 31 | `NF.MIXED_TO_IMPROPER` | Convert mixed number to improper fraction | G5 | 1820 | NF.WHOLE_AS_FRACTION (0.7) | — | whole<=5, denominator<=10 |
| 32 | `NF.SUB_UNLIKE_LCM` | Subtract fractions, unlike denom, requiring LCM | G5 | 1900 | NF.SUB_SAME_SIMPLIFY (0.78)<br>NF.COMMON_DENOM (0.82) | NF.ADD_UNLIKE_LCM (0.6) | coprime denoms, LCM needed, no borrowing |