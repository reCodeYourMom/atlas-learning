"use client";

import { useState } from "react";
import { useLang } from "@/components/LanguageProvider";
import { Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";
import type { TutorExplanation } from "@/lib/types";

/**
 * Tuteur causal interrogeable (Mouvement 04) — le moteur « parle ».
 * Explique « pourquoi cet exercice » à partir du diagnostic cause-racine, à la demande.
 * Déterministe, sans PII : un repli, pas une boucle d'engagement.
 */
export function TutorExplain({ studentId, gapCode }: { studentId: string; gapCode: string }) {
  const { t, lang } = useLang();
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<TutorExplanation | null>(null);
  const [loading, setLoading] = useState(false);

  const toggle = async () => {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (!data) {
      setLoading(true);
      try {
        setData(await api.tutorExplain(studentId, gapCode));
      } finally {
        setLoading(false);
      }
    }
  };

  const headline = data && (lang === "ar" ? data.headline_ar : data.headline_en);
  const why = data && (lang === "ar" ? data.why_ar : data.why_en);

  return (
    <div className="mt-4">
      <button
        onClick={toggle}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:underline"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 16v-4M12 8h.01" strokeLinecap="round" />
        </svg>
        {open ? t("tutor.hide") : t("tutor.why")}
      </button>

      {open && (
        <div className="mt-3 rounded-xl border border-brand-100 bg-white p-4">
          {loading || !data ? (
            <div className="flex items-center gap-2 text-sm text-sand-500">
              <Spinner className="h-4 w-4" /> {t("tutor.loading")}
            </div>
          ) : !data.available ? (
            <p className="text-sm text-sand-500">{t("profile.nogaps.body")}</p>
          ) : (
            <>
              <p className="text-sm font-medium leading-relaxed text-sand-800">{headline}</p>
              {data.steps && data.steps.length > 0 && (
                <ol className="mt-3 space-y-2">
                  {data.steps.map((s, i) => (
                    <li key={s.from_code + s.to_code} className="flex items-start gap-2.5">
                      <span className="num mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand-700">
                        {i + 1}
                      </span>
                      <span className="text-sm text-sand-700">
                        {lang === "ar" ? s.reason_ar : s.reason_en}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
              {why && <p className="mt-3 text-sm text-sand-600">{why}</p>}
              <p className={cx("mt-3 text-[11px] text-sand-400")}>{t("tutor.governance")}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
