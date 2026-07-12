"use client";

import { useLang } from "@/components/LanguageProvider";
import type { StandardRef } from "@/lib/types";

/**
 * Badge B4 à côté d'une compétence. Tooltip = wording par type d'alignement (tables
 * fermées du cadrage, EN/AR selon la langue active) — jamais de texte libre.
 * Rendu UNIQUEMENT si le payload porte `standard` (vue ≠ ATLAS) : zéro régression.
 *
 * Affichage (revue 2026-07-12, CRIT-3) : un `display_code` (CCSS/UK) est un vrai code
 * officiel → chip monospace LTR. MoE UAE n'a PAS de code (`display_code` null) : on
 * affiche le LABEL du domaine en texte normal, jamais la clé technique en font-mono
 * (afficher `NUM_OPS.G4-G5` comme un code du ministère serait faux).
 */
export function StandardBadge({ standard }: { standard?: StandardRef | null }) {
  const { lang } = useLang();
  if (!standard) return null;
  const tooltip = lang === "ar" ? standard.wording_ar : standard.wording_en;

  if (standard.display_code) {
    return (
      <span
        className="inline-flex shrink-0 items-center rounded-md bg-sand-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-sand-600 ring-1 ring-sand-200"
        title={tooltip}
        data-ltr
      >
        {standard.display_code}
      </span>
    );
  }

  // MoE : label du domaine en texte normal, pas de pseudo-code
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-md bg-sand-100 px-1.5 py-0.5 text-[10px] font-medium text-sand-600 ring-1 ring-sand-200"
      title={tooltip}
    >
      {lang === "ar" ? standard.label_ar : standard.label_en}
    </span>
  );
}
