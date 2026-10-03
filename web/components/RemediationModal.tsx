"use client";

import { useEffect, useState } from "react";
import { useLang } from "@/components/LanguageProvider";
import { Button, Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";
import type { RemediationPreview } from "@/lib/types";

/**
 * Déclenchement remédiation (écran C, P0). Montre que l'outil AGIT, pas seulement diagnostique.
 * États : génération en cours → exercice prêt → assigné. L'exercice cible la cause racine.
 */
export function RemediationModal({
  competencyCode,
  onClose,
}: {
  competencyCode: string;
  onClose: () => void;
}) {
  const { t, lang, dir } = useLang();
  const [preview, setPreview] = useState<RemediationPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [assigned, setAssigned] = useState(false);

  useEffect(() => {
    setPreview(null);
    setAssigned(false);
    api
      .remediation(competencyCode, lang)
      .then(setPreview)
      .catch((e) => setError(e.message));
  }, [competencyCode, lang]);

  const targetLabel =
    preview && (lang === "ar" ? preview.competency_label_ar : preview.competency_label_en);

  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-sand-900/40 p-0 sm:items-center sm:p-4"
      onClick={onClose}
      dir={dir}
    >
      <div
        className="w-full max-w-lg animate-fade-up rounded-t-2xl bg-white p-6 shadow-lift sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-sand-800">{t("remediation.title")}</h3>
            <p className="mt-0.5 text-sm text-sand-500">{t("remediation.targets")}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-sand-400 hover:bg-sand-100" aria-label={t("common.close")}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {targetLabel && (
          <div className="mt-4 rounded-xl bg-gold-50 px-4 py-2.5 text-sm font-medium text-gold-700 ring-1 ring-gold-200">
            {targetLabel}
          </div>
        )}

        <div className="mt-4">
          {error && <p className="text-sm text-danger">{error}</p>}

          {!preview && !error && (
            <div className="flex items-center gap-3 py-8 text-sand-500">
              <Spinner /> <span className="text-sm">{t("remediation.generating")}</span>
            </div>
          )}

          {preview && !preview.available && (
            <p className="rounded-xl bg-sand-50 px-4 py-6 text-center text-sm text-sand-500">
              {t("remediation.none")}
            </p>
          )}

          {preview?.available && preview.content && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-sand-400">
                {t("remediation.preview")}
              </p>
              <div className="rounded-xl border border-sand-200 p-4">
                <p className="text-base font-medium text-sand-800">{preview.content.stem}</p>
                {Array.isArray(preview.content.options) && (
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {preview.content.options.map((o, i) => (
                      <span
                        key={i}
                        className="num rounded-lg border border-sand-200 bg-sand-25 px-3 py-2 text-center text-sm text-sand-700"
                      >
                        {o}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t("common.close")}
          </Button>
          {preview?.available && (
            <Button
              variant={assigned ? "primary" : "accent"}
              disabled={assigned}
              onClick={() => setAssigned(true)}
              className={cx(assigned && "bg-mastered hover:bg-mastered")}
            >
              {assigned ? t("remediation.assigned") : t("remediation.assign")}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
