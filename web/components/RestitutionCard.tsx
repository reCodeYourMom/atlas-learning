"use client";

import { useLang } from "@/components/LanguageProvider";
import { Chip } from "@/components/ui";
import type { Restitution } from "@/lib/types";

/**
 * Restitution lisible : percentile + niveau, avec fourchette honnête si confiance basse
 * (Brief §2 — jamais de faux score précis). Une jauge sobre vs attentes du supérieur.
 */
export function RestitutionCard({ r, variant = "staff" }: { r: Restitution; variant?: "staff" | "parent" }) {
  const { t, lang } = useLang();
  if (r.percentile == null) {
    return (
      <div className="rounded-2xl bg-sand-100 px-5 py-4 text-sm text-sand-500">
        {t("common.notmeasured")}
      </div>
    );
  }

  const pct = r.percentile;
  const range = r.percentile_range;
  const target = lang === "ar" ? "جاهزية SAT" : "SAT-ready";

  return (
    <div className="rounded-2xl bg-brand-800 p-5 text-white">
      <div className="flex items-end justify-between gap-4">
        <div>
          {variant === "parent" && <p className="text-sm text-brand-100/80">{t("parent.ontrack")}</p>}
          <p className="mt-0.5 text-2xl font-semibold">
            {variant === "parent" ? (
              <span>{target}</span>
            ) : (
              <span className="num">
                {t("common.level")} {r.level}
              </span>
            )}
          </p>
        </div>
        <div className="text-end">
          <p className="num text-3xl font-semibold text-gold-300">{Math.round(pct)}</p>
          <p className="text-xs text-brand-100/80">{t("common.percentile")}</p>
        </div>
      </div>

      {/* Jauge de position. */}
      <div className="mt-4">
        <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-brand-700" data-ltr>
          {range && (
            <div
              className="absolute inset-y-0 rounded-full bg-brand-500/60"
              style={{ insetInlineStart: `${range[0]}%`, width: `${Math.max(2, range[1] - range[0])}%` }}
            />
          )}
          <div
            className="absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full bg-gold-400 ring-2 ring-brand-800"
            style={{ insetInlineStart: `calc(${pct}% - 8px)` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[11px] text-brand-100/70 num">
          <span>G2</span><span>G3</span><span>G4</span><span>G5</span><span>G6</span>
        </div>
      </div>

      <div className="mt-3">
        {r.measured && !r.is_range ? (
          <Chip className="border-0 bg-white/10 text-white ring-white/20">
            <span className="h-1.5 w-1.5 rounded-full bg-mastered" /> {t("common.measured")}
          </Chip>
        ) : (
          <Chip className="border-0 bg-white/10 text-brand-100 ring-white/20">
            <span className="h-1.5 w-1.5 rounded-full bg-gold-300" /> {t("common.estimated")}
            {range && (
              <span className="num ms-1">
                ({Math.round(range[0])}–{Math.round(range[1])})
              </span>
            )}
          </Chip>
        )}
      </div>
    </div>
  );
}
