"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { useLang } from "@/components/LanguageProvider";
import { Card, ErrorPanel, Loading, cx } from "@/components/ui";
import { RestitutionCard } from "@/components/RestitutionCard";
import { EthicsStance } from "@/components/EthicsStance";
import { api } from "@/lib/api";
import type { NextStep, Trajectory } from "@/lib/types";
import { label } from "@/lib/mastery";

/**
 * Trajectoire de mon enfant (écran I, P1) — mobile-first, lecture seule.
 * Ton rassurant et aspirationnel ; lacune = « prochaine étape », jamais échec (Brief §4).
 */
export default function ParentPage({ params }: { params: { studentId: string } }) {
  return (
    <AppShell narrow>
      <ParentView studentId={params.studentId} />
    </AppShell>
  );
}

function ParentView({ studentId }: { studentId: string }) {
  const { t, lang } = useLang();
  const router = useRouter();
  const [data, setData] = useState<Trajectory | null>(null);
  const [children, setChildren] = useState<{ student_id: string; label: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.studentTrajectory(studentId).then(setData).catch((e) => setError(e.message));
  }, [studentId]);
  useEffect(() => {
    api.parentChildren().then((r) => setChildren(r.children)).catch(() => setChildren([]));
  }, []);

  if (error) return <ErrorPanel detail={error} />;
  if (!data) return <Loading label={t("common.loading")} />;

  return (
    <div className="space-y-5">
      <header>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-sand-800">{t("parent.title")}</h1>
          {children.length > 1 && (
            <select
              value={studentId}
              onChange={(e) => router.replace(`/parent/${e.target.value}`)}
              className="rounded-lg border border-sand-300 bg-white px-2.5 py-1.5 text-sm text-sand-700"
              data-ltr
              aria-label={t("parent.child")}
            >
              {children.map((c) => (
                <option key={c.student_id} value={c.student_id}>{c.label}</option>
              ))}
            </select>
          )}
        </div>
        <p className="mt-1 text-sm text-sand-500">{t("parent.position")}</p>
      </header>

      <RestitutionCard r={data.restitution} variant="parent" />

      {/* Action « 10 min à la maison » — cause racine présentée simplement, sans score (Mouvement 01). */}
      {data.next_step && (
        <Card className="border-gold-200 bg-gold-50/40 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-sand-800">{t("parent.nextstep.title")}</h2>
            <span
              className="num shrink-0 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gold-700 ring-1 ring-gold-200"
              data-ltr
            >
              {t("parent.nextstep.minutes").replace("{n}", String(data.next_step.minutes))}
            </span>
          </div>
          <p className="mt-1 text-sm text-sand-500">{t("parent.nextstep.intro")}</p>
          <div className="mt-3 rounded-xl border border-sand-200 bg-white p-3.5">
            <p className="text-xs uppercase tracking-wide text-sand-400">{t("parent.nextstep.focus")}</p>
            <p className="mt-0.5 text-sm font-medium text-sand-800">
              {lang === "ar" ? data.next_step.skill_label_ar : data.next_step.skill_label_en}
            </p>
            <NextStepExample step={data.next_step} />
          </div>
        </Card>
      )}

      {/* Acquis valorisés. */}
      <Card className="p-5">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-full bg-emerald-50 text-mastered">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <div>
            <p className="num text-2xl font-semibold text-sand-800">{data.n_mastered}</p>
            <p className="text-sm text-sand-500">{t("parent.mastered.count")}</p>
          </div>
        </div>
      </Card>

      {/* Lacunes présentées comme « en cours de comblement ». */}
      <Card className="p-5">
        <h2 className="text-base font-semibold text-sand-800">{t("parent.closing")}</h2>
        <p className="mt-0.5 text-sm text-sand-500">{t("parent.reassure")}</p>

        <ul className="mt-4 space-y-3">
          {data.closing_gaps.length === 0 && (
            <li className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              {t("profile.nogaps.body")}
            </li>
          )}
          {data.closing_gaps.map((g, i) => (
            <li key={i} className="rounded-xl border border-sand-200 p-3.5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-sand-800">{label(g, lang)}</p>
                <span className="num text-xs font-medium text-gold-700">{g.progress}%</span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-sand-100" data-ltr>
                <div
                  className={cx("bar-fill h-full rounded-full bg-progress", g.confidence < 0.5 && "opacity-50")}
                  style={{ width: `${g.progress}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      </Card>

      {/* Parti pris éthique : pas de streak, pas de classement — rassurant côté parent. */}
      <EthicsStance />
    </div>
  );
}

/** Exemple d'exercice (sans la réponse) ou repli « fais-le expliquer par ton enfant ». */
function NextStepExample({ step }: { step: NextStep }) {
  const { t, lang } = useLang();
  const example =
    (lang === "ar" ? step.activity?.example_ar : step.activity?.example_en) ??
    step.activity?.example_en ??
    step.activity?.example_ar ??
    null;
  if (!example) {
    return <p className="mt-3 text-sm text-sand-600">{t("parent.nextstep.noexample")}</p>;
  }
  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-gold-700">{t("parent.nextstep.example")}</p>
      <p className="mt-1 rounded-lg bg-sand-50 px-3 py-2 text-sm text-sand-700">{example}</p>
    </div>
  );
}
