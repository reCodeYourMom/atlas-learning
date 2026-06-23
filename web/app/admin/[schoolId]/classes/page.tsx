"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useLang } from "@/components/LanguageProvider";
import { Button, Card, ErrorPanel, Loading, SectionTitle, cx } from "@/components/ui";
import { api } from "@/lib/api";
import type { SchoolOverview } from "@/lib/types";
import { eloToLevel } from "@/lib/mastery";

export default function ClassesPage({ params }: { params: { schoolId: string } }) {
  return (
    <AppShell>
      <Classes schoolId={params.schoolId} />
    </AppShell>
  );
}

function Classes({ schoolId }: { schoolId: string }) {
  const { t, lang } = useLang();
  const [data, setData] = useState<SchoolOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.schoolOverview(schoolId).then(setData).catch((e) => setError(e.message));
  }, [schoolId]);

  if (error) return <ErrorPanel detail={error} />;
  if (!data) return <Loading label={t("common.loading")} />;

  const totalStudents = data.n_students;
  const licencesTotal = Math.max(40, Math.ceil(totalStudents / 10) * 10); // capacité provisionnée
  const usedPct = Math.round((totalStudents / licencesTotal) * 100);

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-sand-800">{t("classes.title")}</h1>
          <p className="mt-1 text-sm text-sand-500">{t("classes.subtitle")}</p>
        </div>
        <Button variant="primary">+ {t("classes.add")}</Button>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Licences. */}
        <Card className="p-5">
          <SectionTitle title={t("classes.licences")} />
          <p className="num text-3xl font-semibold text-brand-700">
            {totalStudents}
            <span className="text-base font-normal text-sand-400"> / {licencesTotal}</span>
          </p>
          <p className="mt-1 text-xs text-sand-500">{t("classes.used")}</p>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-sand-100" data-ltr>
            <div className="bar-fill h-full rounded-full bg-brand-500" style={{ width: `${usedPct}%` }} />
          </div>
        </Card>

        {/* Table classes. */}
        <Card className="p-5 lg:col-span-2">
          <SectionTitle title={t("nav.classes")} />
          <div className="overflow-hidden rounded-xl ring-1 ring-sand-200">
            <table className="w-full text-sm">
              <thead className="bg-sand-50 text-xs uppercase tracking-wide text-sand-500">
                <tr>
                  <th className="px-3 py-2 text-start font-medium">{t("classes.col.name")}</th>
                  <th className="px-2 py-2 text-center font-medium">{t("classes.col.students")}</th>
                  <th className="px-2 py-2 text-center font-medium">{t("classes.col.avg")}</th>
                  <th className="px-2 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-sand-100">
                {data.classes.map((c) => (
                  <tr key={c.classroom_id} className="hover:bg-sand-25">
                    <td className="px-3 py-2.5 font-medium text-sand-800">{c.name}</td>
                    <td className="num px-2 py-2.5 text-center text-sand-600">{c.n_students}</td>
                    <td className="num px-2 py-2.5 text-center text-sand-600">{eloToLevel(c.mean_ability)}</td>
                    <td className="px-2 py-2.5 text-end">
                      <button className="text-xs font-medium text-brand-600 hover:underline">
                        {t("classes.invite")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={cx("mt-3 text-xs text-sand-400", lang === "ar" && "text-right")}>
            {lang === "ar"
              ? "تجهيز الصفوف والدعوات متاح في إصدار التشغيل التجريبي."
              : "Class provisioning & invitations are enabled in the pilot deployment."}
          </p>
        </Card>
      </div>
    </div>
  );
}
