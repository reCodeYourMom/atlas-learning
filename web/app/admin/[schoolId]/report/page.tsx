"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useLang } from "@/components/LanguageProvider";
import { Button, ErrorPanel, Loading, cx } from "@/components/ui";
import { api } from "@/lib/api";
import type { ProofSurfaces, SchoolOverview } from "@/lib/types";

export default function ReportPage({ params }: { params: { schoolId: string } }) {
  return (
    <AppShell>
      <Report schoolId={params.schoolId} />
    </AppShell>
  );
}

function Report({ schoolId }: { schoolId: string }) {
  const { t, lang } = useLang();
  const [data, setData] = useState<SchoolOverview | null>(null);
  const [proof, setProof] = useState<ProofSurfaces | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.schoolOverview(schoolId), api.schoolProof(schoolId)])
      .then(([o, p]) => {
        setData(o);
        setProof(p);
      })
      .catch((e) => setError(e.message));
  }, [schoolId]);

  if (error) return <ErrorPanel detail={error} />;
  if (!data) return <Loading label={t("common.loading")} />;

  const avgMastery =
    data.competencies.length > 0
      ? data.competencies.reduce((a, c) => a + c.mastery_rate, 0) / data.competencies.length
      : 0;
  const strongest = [...data.competencies].sort((a, b) => b.mastery_rate - a.mastery_rate).slice(0, 5);
  const weakest = data.competencies.slice(0, 5); // déjà triées faibles d'abord

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between print:hidden">
        <div>
          <h1 className="text-2xl font-semibold text-sand-800">{t("report.title")}</h1>
          <p className="mt-1 text-sm text-sand-500">{t("report.subtitle")}</p>
        </div>
        <Button variant="accent" onClick={() => window.print()}>
          {t("report.print")}
        </Button>
      </div>

      {/* Document — registre institutionnel, sobre. */}
      <div className="mx-auto max-w-3xl rounded-2xl bg-white p-8 shadow-card ring-1 ring-sand-200 print:max-w-none print:shadow-none print:ring-0">
        <header className="flex items-center justify-between border-b border-sand-200 pb-5">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 text-white">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" strokeLinejoin="round" />
              </svg>
            </span>
            <div>
              <p className="font-semibold text-brand-800">{t("app.name")}</p>
              <p className="text-xs text-sand-500">{t("report.title")}</p>
            </div>
          </div>
          <p className="text-xs text-sand-400">
            {t("report.generated")}: <span className="num">{today()}</span>
          </p>
        </header>

        <div className="mt-6 grid grid-cols-3 gap-4">
          <Metric value={data.n_students} label={t("school.kpi.students")} />
          <Metric value={data.classes.length} label={t("school.kpi.classes")} />
          <Metric value={`${Math.round(avgMastery * 100)}%`} label={t("school.kpi.mastery")} />
        </div>

        {proof && <ProofBlock proof={proof} />}

        <div className="mt-8 grid gap-8 sm:grid-cols-2">
          <ReportList
            title={lang === "ar" ? "أقوى المهارات" : "Strongest skills"}
            rows={strongest}
            tone="mastered"
          />
          <ReportList
            title={lang === "ar" ? "مهارات ذات أولوية" : "Priority skills"}
            rows={weakest}
            tone="progress"
          />
        </div>

        <div className="mt-8">
          <h3 className="mb-2 text-sm font-semibold text-sand-700">{t("school.byclass")}</h3>
          <table className="w-full text-sm">
            <tbody className="divide-y divide-sand-100">
              {data.classes.map((c) => (
                <tr key={c.classroom_id}>
                  <td className="py-2 text-sand-700">{c.name}</td>
                  <td className="num py-2 text-end text-sand-500">
                    {c.n_students} {t("common.students")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <footer className="mt-8 border-t border-sand-200 pt-4 text-[11px] text-sand-400">
          {lang === "ar"
            ? "بيانات مُجمَّعة دون معلومات تعريف شخصية. تقرير قابل للمشاركة مع العائلات والجهة المنظِّمة."
            : "Aggregated data, no personally identifiable student information. Shareable with families and the regulator."}
        </footer>
      </div>
    </div>
  );
}

function ProofBlock({ proof }: { proof: ProofSurfaces }) {
  const { t, lang } = useLang();
  const { cohort, gains, trajectory } = proof;
  const pct = (v: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);
  const hasData = cohort.before != null && cohort.after != null;
  const maxBand = Math.max(1, ...trajectory.map((b) => b.n_students));

  return (
    <section className="mt-8 rounded-xl border border-brand-100 bg-brand-50/40 p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-brand-800">{t("proof.title")}</h3>
        <span className="text-[11px] text-sand-500">
          {t("proof.subtitle").replace("{n}", String(cohort.window_days))}
        </span>
      </div>

      {!hasData ? (
        <p className="mt-3 text-sm text-sand-500">{t("proof.nodata")}</p>
      ) : (
        <>
          {/* Avant / après cohorte — le récit d'impact. */}
          <div className="mt-4 flex items-center gap-4">
            <BeforeAfter label={t("proof.before")} value={pct(cohort.before)} tone="muted" />
            <span className="text-brand-300 rtl-flip" aria-hidden>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <BeforeAfter label={t("proof.after")} value={pct(cohort.after)} tone="strong" />
            {cohort.delta != null && cohort.delta !== 0 && (
              <span
                className={cx(
                  "num ms-1 rounded-md px-2 py-0.5 text-xs font-semibold",
                  cohort.delta > 0 ? "bg-emerald-50 text-emerald-700" : "bg-gold-50 text-gold-700",
                )}
              >
                {cohort.delta > 0 ? "+" : ""}
                {Math.round(cohort.delta * 100)} pts
              </span>
            )}
            <span className="num ms-auto text-[11px] text-sand-400">{t("proof.cohort")}</span>
          </div>

          {/* Plus gros gains par compétence. */}
          {gains.length > 0 && (
            <div className="mt-5">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sand-500">
                {t("proof.gains")}
              </h4>
              <ul className="space-y-1.5">
                {gains.slice(0, 4).map((g) => (
                  <li key={g.competency_code} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate text-sand-700">{lang === "ar" ? g.label_ar : g.label_en}</span>
                    <span className="num shrink-0 text-xs text-sand-500" data-ltr>
                      {Math.round(g.before * 100)}% → {Math.round(g.after * 100)}%
                      <span
                        className={cx(
                          "ms-2 font-semibold",
                          g.delta >= 0 ? "text-emerald-700" : "text-gold-700",
                        )}
                      >
                        {g.delta >= 0 ? "+" : ""}
                        {Math.round(g.delta * 100)}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Projection trajectoire — distribution de la cohorte par niveau. */}
      <div className="mt-5">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sand-500">
          {t("proof.trajectory")}
        </h4>
        <div className="flex items-end gap-2" data-ltr>
          {trajectory.map((b) => (
            <div key={b.level} className="flex flex-1 flex-col items-center gap-1">
              <span className="num text-[11px] text-sand-500">{b.n_students}</span>
              <div
                className="w-full rounded-t bg-brand-400"
                style={{ height: `${8 + (b.n_students / maxBand) * 56}px` }}
              />
              <span className="num text-[11px] font-medium text-sand-600">{b.level}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-4 text-[11px] text-sand-400">{t("proof.honest")}</p>
    </section>
  );
}

function BeforeAfter({ label, value, tone }: { label: string; value: string; tone: "muted" | "strong" }) {
  return (
    <div className="text-center">
      <p className="text-[11px] uppercase tracking-wide text-sand-400">{label}</p>
      <p className={cx("num text-2xl font-semibold", tone === "strong" ? "text-brand-700" : "text-sand-500")}>
        {value}
      </p>
    </div>
  );
}

function Metric({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="rounded-xl bg-sand-50 px-4 py-3 text-center">
      <p className="num text-2xl font-semibold text-brand-700">{value}</p>
      <p className="mt-0.5 text-xs text-sand-500">{label}</p>
    </div>
  );
}

function ReportList({
  title,
  rows,
  tone,
}: {
  title: string;
  rows: SchoolOverview["competencies"];
  tone: "mastered" | "progress";
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-sand-700">{title}</h3>
      <ul className="space-y-1.5">
        {rows.map((c) => (
          <li key={c.code} className="flex items-center justify-between gap-2 text-sm">
            <span className="truncate text-sand-700">{c.label}</span>
            <span
              className={cx(
                "num shrink-0 rounded-md px-2 py-0.5 text-xs font-medium",
                tone === "mastered" ? "bg-emerald-50 text-emerald-700" : "bg-gold-50 text-gold-700",
              )}
            >
              {Math.round(c.mastery_rate * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
