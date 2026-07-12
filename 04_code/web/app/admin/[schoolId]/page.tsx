"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useLang } from "@/components/LanguageProvider";
import { Card, ErrorPanel, Loading, SectionTitle } from "@/components/ui";
import { SkillBarChart } from "@/components/SkillBarChart";
import { api } from "@/lib/api";
import type { SchoolOverview } from "@/lib/types";
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
          <SectionTitle title={t("school.byclass")} />
          <ul className="space-y-2">
            {data.classes.map((c) => (
              <li
                key={c.classroom_id}
                className="flex items-center justify-between rounded-xl border border-sand-200 bg-white px-4 py-3"
              >
                <div>
                  <p className="font-medium text-sand-800">{c.name}</p>
                  <p className="num text-xs text-sand-400">
                    {c.n_students} {t("common.students")}
                  </p>
                </div>
                <span className="num rounded-lg bg-brand-50 px-2.5 py-1 text-sm font-semibold text-brand-700">
                  {eloToLevel(c.mean_ability)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
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
