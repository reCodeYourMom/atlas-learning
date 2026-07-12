"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useLang } from "@/components/LanguageProvider";
import { Button, Card, Chip, EmptyState, ErrorPanel, Loading, SectionTitle, cx } from "@/components/ui";
import { api } from "@/lib/api";
import type { ArCoverage, ArItem } from "@/lib/types";

/**
 * Console linguiste (Mouvement 02) — « faire descendre l'arabe dans le contenu ».
 * La machine (Groq/ALLaM) PROPOSE, le linguiste VALIDE. Le gate ar_validated reste
 * la seule porte vers le pool servi aux élèves.
 */
export default function ArabicConsolePage() {
  return (
    <AppShell>
      <ArabicConsole />
    </AppShell>
  );
}

function ArabicConsole() {
  const { t } = useLang();
  const [items, setItems] = useState<ArItem[] | null>(null);
  const [coverage, setCoverage] = useState<ArCoverage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api
      .arPending()
      .then((r) => {
        setItems(r.items);
        setCoverage(r.coverage);
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  if (error) return <ErrorPanel detail={error} />;
  if (!items || !coverage) return <Loading label={t("common.loading")} />;

  const pct = Math.round(coverage.pct_validated * 100);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-sand-800">{t("ar.title")}</h1>
        <p className="mt-1 text-sm text-sand-500">{t("ar.subtitle")}</p>
      </header>

      {/* Couverture AR — preuve mesurable de la descente (prérequis KSA). */}
      <Card className="p-5">
        <div className="flex items-center justify-between gap-3">
          <SectionTitle title={t("ar.coverage")} />
          <span className="num text-sm font-semibold text-sand-800">
            {coverage.ar_validated}{" "}
            <span className="font-normal text-sand-500">
              {t("ar.coverage.of").replace("{n}", String(coverage.total_items))}
            </span>
          </span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-sand-100" data-ltr>
          <div className="bar-fill h-full rounded-full bg-mastered" style={{ width: `${pct}%` }} />
        </div>
      </Card>

      <Card className="p-5">
        <SectionTitle title={`${t("ar.pending.title")} · ${items.length}`} />
        {items.length === 0 ? (
          <EmptyState title={t("ar.none")} body={t("ar.subtitle")} />
        ) : (
          <ul className="space-y-3">
            {items.map((it) => (
              <ArRow key={it.item_id} item={it} onChanged={load} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function ArRow({ item, onChanged }: { item: ArItem; onChanged: () => void }) {
  const { t } = useLang();
  const [busy, setBusy] = useState<"propose" | "validate" | null>(null);
  const [local, setLocal] = useState<ArItem>(item);

  const propose = async () => {
    setBusy("propose");
    try {
      setLocal(await api.arPropose(item.item_id));
    } finally {
      setBusy(null);
    }
  };
  const validate = async () => {
    setBusy("validate");
    try {
      await api.arValidate(item.item_id);
      onChanged(); // l'item quitte la worklist (linguist_validated)
    } finally {
      setBusy(null);
    }
  };

  return (
    <li className="rounded-xl border border-sand-200 p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-sand-400">{t("ar.en")}</p>
          <p className="mt-1 text-sm text-sand-800" data-ltr>
            {local.content_en.stem}
          </p>
        </div>
        <div>
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-wide text-sand-400">{t("ar.ar")}</p>
            {local.content_ar && (
              <Chip
                className={cx(
                  local.math_preserved
                    ? "bg-emerald-50 text-emerald-800 ring-emerald-200"
                    : "bg-gold-50 text-gold-700 ring-gold-200",
                )}
              >
                {local.math_preserved ? t("ar.math.ok") : t("ar.math.warn")}
              </Chip>
            )}
          </div>
          <p className="mt-1 text-sm text-sand-800" dir="rtl">
            {local.content_ar?.stem ?? <span className="text-sand-400">{t("ar.notyet")}</span>}
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-end gap-2">
        <Button variant="outline" onClick={propose} disabled={busy !== null}>
          {busy === "propose" ? t("ar.proposing") : t("ar.propose")}
        </Button>
        <Button variant="accent" onClick={validate} disabled={busy !== null || !local.content_ar}>
          {t("ar.validate")}
        </Button>
      </div>
    </li>
  );
}
