"use client";

import { useLang } from "@/components/LanguageProvider";
import { Button, Chip, cx } from "@/components/ui";
import type { Diagnosis } from "@/lib/types";

/**
 * Le composant héros (Brief §9). Rend une lacune comme une CHAÎNE causale lisible :
 * prérequis racine → … → compétence en échec, lue dans le sens de lecture (LTR/RTL).
 * Doublé d'une formulation en langage naturel (« bloque sur X parce que Y »),
 * car c'est ce qu'un directeur répétera.
 */
export function DiagnosisBlock({
  d,
  onRemediate,
}: {
  d: Diagnosis;
  onRemediate?: (rootCauseCode: string) => void;
}) {
  const { lang, t } = useLang();

  // chain = [gap, …, root_cause]. On lit racine → gap (le prérequis « débloque » la compétence).
  const ordered = [...d.chain].reverse(); // [root_cause, …, gap]
  const srcLabels = lang === "ar" ? d.chain_labels_ar : d.chain_labels;
  const labels = [...srcLabels].reverse();

  const sentence = buildSentence(d, lang);

  return (
    <div className="rounded-2xl bg-gradient-to-b from-brand-50 to-white p-5 ring-1 ring-brand-100">
      {/* Langage naturel — la phrase que le directeur retiendra. */}
      <p className="text-base leading-relaxed text-sand-800 sm:text-lg">{sentence}</p>

      {/* Chaîne visuelle. */}
      {d.is_self ? (
        <div className="mt-4">
          <ChainNode label={d.gap_label} role="self" />
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-stretch gap-2">
          {ordered.map((code, i) => {
            const isRoot = i === 0;
            const isGap = i === ordered.length - 1;
            return (
              <div key={code} className="flex items-stretch gap-2">
                <ChainNode label={labels[i]} role={isRoot ? "root" : isGap ? "gap" : "mid"} />
                {i < ordered.length - 1 && <Arrow />}
              </div>
            );
          })}
        </div>
      )}

      {onRemediate && (
        <div className="mt-5 flex items-center justify-between gap-3">
          <span className="text-xs text-sand-500">{t("remediation.targets")}</span>
          {/* Accent or = LE focal point de l'écran : agir, pas seulement diagnostiquer. */}
          <Button variant="accent" onClick={() => onRemediate(d.root_cause)}>
            {t("profile.remediate")}
          </Button>
        </div>
      )}
    </div>
  );
}

function ChainNode({ label, role }: { label: string; role: "root" | "mid" | "gap" | "self" }) {
  const { t } = useLang();
  const styles = {
    root: "border-gold-300 bg-gold-50 ring-2 ring-gold-300",
    mid: "border-sand-300 bg-white",
    gap: "border-brand-200 bg-brand-50",
    self: "border-brand-200 bg-brand-50",
  } as const;
  const tag =
    role === "root" ? t("profile.rootcause") : role === "gap" || role === "self" ? t("profile.blockedon") : null;
  const tagStyle = role === "root" ? "text-gold-700" : "text-brand-600";

  return (
    <div className={cx("flex min-w-[8.5rem] max-w-[12rem] flex-col rounded-xl border px-3 py-2.5", styles[role])}>
      {tag && <span className={cx("text-[10px] font-semibold uppercase tracking-wide", tagStyle)}>{tag}</span>}
      <span className="mt-0.5 text-sm font-medium leading-snug text-sand-800">{label}</span>
    </div>
  );
}

function Arrow() {
  // Chevron directionnel — se miroite en RTL (rtl-flip).
  return (
    <div className="flex items-center text-brand-300 rtl-flip" aria-hidden>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function buildSentence(d: Diagnosis, lang: "en" | "ar") {
  const gap = lang === "ar" ? d.gap_label_ar : d.gap_label;
  const root = lang === "ar" ? d.root_cause_label_ar : d.root_cause_label;
  if (d.is_self) {
    return lang === "ar"
      ? `ثغرة في «${gap}» نفسها — لا يوجد متطلّب سابق ناقص.`
      : `A gap on “${gap}” itself — no missing prerequisite.`;
  }
  return lang === "ar"
    ? `متعثّر في «${gap}» لأنّ «${root}» غير مُتقَنة بعد.`
    : `Blocked on “${gap}” because “${root}” isn't mastered yet.`;
}
