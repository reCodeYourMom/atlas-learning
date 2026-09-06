"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useLang } from "@/components/LanguageProvider";
import { Card, Chip, ErrorPanel, Loading, SectionTitle, cx } from "@/components/ui";
import { SkillBarChart } from "@/components/SkillBarChart";
import { StandardBadge } from "@/components/StandardBadge";
import { api } from "@/lib/api";
import type { ClassSummary, SchoolOverview } from "@/lib/types";
import { eloToLevel } from "@/lib/mastery";

export default function AdminDashboardPage({ params }: { params: { schoolId: string } }) {
  return (
    <AppShell>
      <Dashboard schoolId={params.schoolId} />
    </AppShell>
  );
}

function Dashboard({ schoolId }: { schoolId: string }) {
  const { t } = useLang();
  const [data, setData] = useState<SchoolOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.schoolOverview(schoolId).then(setData).catch((e) => setError(e.message));
  }, [schoolId]);

  if (error) return <ErrorPanel detail={error} />;
  if (!data) return <Loading label={t("common.loading")} />;

  const avgMastery =
    data.competencies.length > 0
      ? data.competencies.reduce((a, c) => a + c.mastery_rate, 0) / data.competencies.length
      : 0;

  const chart = data.competencies
    .slice(0, 12)
    .map((c) => ({ label: c.label, rate: c.mastery_rate, n: c.n_measured }));

  // Le back trie déjà : la plus en difficulté d'abord. On ne met en avant une classe que
  // si l'écart avec la suivante est RÉEL — sinon on afficherait « à surveiller » sur une
  // cohorte homogène, et le signal ne voudrait plus rien dire.
  const rates = data.classes.map((c) => c.mastery_rate).filter((r): r is number => r != null);
  const spread = rates.length > 1 ? Math.max(...rates) - Math.min(...rates) : 0;
  const focus = spread >= 0.15 ? data.classes[0] : null;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-sand-800">{t("school.title")}</h1>
        <p className="mt-1 text-sm text-sand-500">{t("school.subtitle")}</p>
      </header>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi value={data.n_students} label={t("school.kpi.students")} />
        <Kpi value={data.classes.length} label={t("school.kpi.classes")} />
        <Kpi value={data.competencies.length} label={t("school.kpi.skills")} />
        <Kpi value={`${Math.round(avgMastery * 100)}%`} label={t("school.kpi.mastery")} accent />
      </div>

      {/* Étape 1 du parcours : la classe qui décroche, nommée avec SA cause, et cliquable. */}
      {focus && <FocusBanner schoolId={schoolId} cls={focus} />}

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="p-5 lg:col-span-3">
          <SectionTitle title={t("school.byskill")} />
          {chart.length > 0 ? (
            <SkillBarChart data={chart} />
          ) : (
            <p className="py-10 text-center text-sm text-sand-400">{t("common.notmeasured")}</p>
          )}
        </Card>

        <Card className="p-5 lg:col-span-2">
          <SectionTitle title={t("school.byclass")} subtitle={t("school.byclass.hint")} />
          <ul className="space-y-2">
            {data.classes.map((c, i) => (
              <ClassRow
                key={c.classroom_id}
                cls={c}
                highlight={focus?.classroom_id === c.classroom_id}
                rank={i + 1}
              />
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

/** Bandeau de tête : « cette classe décroche, et voici sur quoi ». */
function FocusBanner({ schoolId, cls }: { schoolId: string; cls: ClassSummary }) {
  const { t, lang } = useLang();
  const w = cls.weakest_competency;
  const label = w ? (lang === "ar" ? w.label_ar || w.label : w.label) : null;

  return (
    <Card className="border-gold-300 bg-gold-50/60 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-gold-700">
            {t("school.focus.eyebrow")}
          </p>
          <p className="mt-1 text-lg font-semibold text-sand-800">
            {cls.name}
            {cls.mastery_rate != null && (
              <span className="num ms-2 text-base font-medium text-gold-700">
                {Math.round(cls.mastery_rate * 100)}% {t("school.focus.mastered")}
              </span>
            )}
          </p>
          {label && (
            <p className="mt-1.5 flex flex-wrap items-center gap-1.5 text-sm text-sand-700">
              {t("school.focus.weakest")}{" "}
              <span className="font-medium text-sand-900">{label}</span>
              <StandardBadge standard={w?.standard} />
              {w && (
                <span className="num text-xs text-sand-500">
                  · {Math.round(w.mastery_rate * 100)}% · {w.n_measured} {t("common.students")}
                </span>
              )}
            </p>
          )}
        </div>
        <Link
          href={`/teacher/${cls.classroom_id}`}
          className="shrink-0 rounded-lg bg-gold-600 px-4 py-2 text-sm font-medium text-white hover:bg-gold-700"
        >
          {t("school.focus.open")} →
        </Link>
      </div>
    </Card>
  );
}

function ClassRow({
  cls,
  highlight,
  rank,
}: {
  cls: ClassSummary;
  highlight: boolean;
  rank: number;
}) {
  const { t, lang } = useLang();
  const w = cls.weakest_competency;
  const label = w ? (lang === "ar" ? w.label_ar || w.label : w.label) : null;
  const pct = cls.mastery_rate != null ? Math.round(cls.mastery_rate * 100) : null;

  return (
    <li>
      <Link
        href={`/teacher/${cls.classroom_id}`}
        className={cx(
          "block rounded-xl border px-4 py-3 transition-colors",
          highlight
            ? "border-gold-300 bg-gold-50/50 hover:border-gold-400"
            : "border-sand-200 bg-white hover:border-brand-300",
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="flex items-center gap-2 font-medium text-sand-800">
              <span className="num text-xs text-sand-400">{rank}</span>
              {cls.name}
            </p>
            <p className="num mt-0.5 text-xs text-sand-400">
              {cls.n_students} {t("common.students")} · {t("common.level")}{" "}
              {eloToLevel(cls.mean_ability)}
            </p>
          </div>
          {pct != null && (
            <Chip
              className={cx(
                "num shrink-0",
                pct >= 75
                  ? "bg-emerald-50 text-emerald-800 ring-emerald-200"
                  : pct >= 50
                    ? "bg-brand-50 text-brand-700 ring-brand-200"
                    : "bg-gold-50 text-gold-700 ring-gold-200",
              )}
            >
              {pct}%
            </Chip>
          )}
        </div>
        {/* Le domaine faible est la vraie information : sans lui, la ligne ne dit qu'un rang. */}
        {label && (
          <p className="mt-2 truncate text-xs text-sand-500">
            {t("school.class.weakest")} <span className="text-sand-700">{label}</span>
          </p>
        )}
      </Link>
    </li>
  );
}

function Kpi({ value, label, accent }: { value: number | string; label: string; accent?: boolean }) {
  return (
    <Card className="p-4">
      <p className={`num text-2xl font-semibold ${accent ? "text-gold-600" : "text-brand-700"}`}>{value}</p>
      <p className="mt-0.5 text-xs text-sand-500">{label}</p>
    </Card>
  );
}
