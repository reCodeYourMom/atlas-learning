"use client";

import { useLang } from "@/components/LanguageProvider";
import { Card } from "@/components/ui";

/**
 * Parti pris éthique affiché (Mouvement 04, À REFUSER) — assumer l'absence de streak/classement
 * comme un CHOIX, pas un manque. Côté régulateur GCC c'est un argument de gouvernance IA ;
 * `variant="governance"` insiste sur les garde-fous techniques (page sécurité/IT).
 */
export function EthicsStance({ variant = "default" }: { variant?: "default" | "governance" }) {
  const { t } = useLang();
  return (
    <Card className="border-brand-100 bg-brand-50/40 p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-600 text-white">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 3l8 4.5v5c0 4.5-3 7-8 8.5-5-1.5-8-4-8-8.5v-5L12 3z" strokeLinejoin="round" />
            <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <div>
          <h3 className="text-base font-semibold text-sand-800">{t("ethics.title")}</h3>
          <p className="mt-1 text-sm leading-relaxed text-sand-600">{t("ethics.body")}</p>
          {variant === "governance" && (
            <div className="mt-3 rounded-lg bg-white p-3 ring-1 ring-sand-200">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                {t("ethics.governance.title")}
              </p>
              <p className="mt-1 text-sm text-sand-600">{t("ethics.governance.body")}</p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
