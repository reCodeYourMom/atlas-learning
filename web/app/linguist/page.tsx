"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useLang } from "@/components/LanguageProvider";
import { Button, Card, Chip, EmptyState, ErrorPanel, Loading, SectionTitle, cx } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { LinguistItem, LinguistQueue } from "@/lib/types";

/**
 * Back-office LINGUISTE (persona dédié, Mouvement 02) — file de validation de l'arabe.
 * La banque est traduite par ALLaM mais rien n'est validé : le linguiste relit, corrige et
 * valide. Les items flaggés « math ⚠️ » (fidélité douteuse) remontent en tête. Le gate
 * ar_validated reste la seule porte vers le pool servi aux élèves.
 */
export default function LinguistQueuePage() {
  return (
    <AppShell>
      <Queue />
    </AppShell>
  );
}

function Queue() {
  const { t } = useLang();
  const [data, setData] = useState<LinguistQueue | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    api
      .linguistQueue()
      .then(setData)
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  if (error) return <ErrorPanel detail={error} />;
  if (!data) return <Loading label={t("common.loading")} />;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-sand-800">{t("ling.title")}</h1>
        <p className="mt-1 text-sm text-sand-500">{t("ling.subtitle")}</p>
      </header>

      <Card className="p-5">
        <SectionTitle title={t("ling.remaining").replace("{n}", String(data.remaining))} />
        {data.items.length === 0 ? (
          <EmptyState title={t("ling.none")} body={t("ling.subtitle")} />
        ) : (
          <ul className="space-y-3">
            {data.items.map((it) => (
              <Row key={it.item_id} item={it} onChanged={load} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

// Sérialise le champ AR (stem + options + answer) en texte éditable, et re-parse à la sauvegarde.
function toDraft(it: LinguistItem): string {
  const ar = it.content_ar ?? { stem: "", options: it.content_en.options ?? [], answer: it.content_en.answer ?? "" };
  return JSON.stringify(ar, null, 2);
}

function Row({ item, onChanged }: { item: LinguistItem; onChanged: () => void }) {
  const { t } = useLang();
  const [local, setLocal] = useState<LinguistItem>(item);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => toDraft(item));
  const [flagOpen, setFlagOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<"save" | "validate" | "flag" | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setBusy("save");
    setErr(null);
    try {
      const parsed = JSON.parse(draft) as Record<string, unknown>;
      const updated = await api.linguistEditArabic(local.item_id, parsed);
      setLocal(updated);
      setDraft(toDraft(updated));
      setEditing(false);
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const validate = async () => {
    setBusy("validate");
    setErr(null);
    try {
      await api.linguistValidate(local.item_id);
      onChanged(); // l'item quitte la file (linguist_validated)
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : (e as Error).message);
      setBusy(null);
    }
  };

  const flag = async () => {
    if (!reason.trim()) return;
    setBusy("flag");
    setErr(null);
    try {
      const updated = await api.linguistFlag(local.item_id, reason.trim());
      setLocal(updated);
      setFlagOpen(false);
      setReason("");
    } catch (e) {
      setErr(e instanceof ApiError ? e.detail : (e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <li className="rounded-xl border border-sand-200 p-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Anglais (source) — LTR. */}
        <div>
          <p className="text-xs uppercase tracking-wide text-sand-400">{t("ling.en")}</p>
          <p className="mt-1 text-sm text-sand-800" dir="ltr">
            {local.content_en.stem}
          </p>
          {local.content_en.options && (
            <p className="mt-1 text-xs text-sand-500" dir="ltr">
              {t("ling.options")}: {local.content_en.options.join(" · ")}
            </p>
          )}
          <p className="mt-1 text-xs text-sand-500" dir="ltr">
            {t("ling.answer")}: {local.content_en.answer}
          </p>
        </div>

        {/* Arabe (à valider) — RTL. */}
        <div>
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-wide text-sand-400">{t("ling.ar")}</p>
            {(local.ar_math_broken || (local.content_ar && !local.math_preserved)) && (
              <Chip className="bg-gold-50 text-gold-700 ring-gold-200">{t("ling.math.warn")}</Chip>
            )}
            {local.content_ar && local.math_preserved && !local.ar_math_broken && (
              <Chip className="bg-emerald-50 text-emerald-800 ring-emerald-200">{t("ling.math.ok")}</Chip>
            )}
          </div>
          {editing ? (
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              dir="rtl"
              rows={6}
              className="mt-1 w-full rounded-lg border border-sand-300 bg-white p-2 font-mono text-xs outline-none focus:border-brand-400"
            />
          ) : (
            <p className="mt-1 text-sm text-sand-800" dir="rtl">
              {local.content_ar?.stem ?? <span className="text-sand-400">{t("ling.notyet")}</span>}
            </p>
          )}
          {local.provenance.flag_reason && (
            <p className="mt-1 text-xs text-gold-700" dir="auto">
              {t("ling.flagged")}: {local.provenance.flag_reason}
            </p>
          )}
        </div>
      </div>

      {err && <p className="mt-3 text-sm text-danger" dir="auto">{err}</p>}

      {flagOpen ? (
        <div className="mt-4 space-y-2">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t("ling.flag.reason")}
            dir="auto"
            className="w-full rounded-lg border border-sand-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-400"
          />
          <div className="flex items-center justify-end gap-2">
            <Button variant="ghost" onClick={() => setFlagOpen(false)} disabled={busy !== null}>
              {t("ling.cancel")}
            </Button>
            <Button variant="outline" onClick={flag} disabled={busy !== null || !reason.trim()}>
              {t("ling.flag.submit")}
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
          <Button variant="ghost" onClick={() => setFlagOpen(true)} disabled={busy !== null}>
            {t("ling.flag")}
          </Button>
          {editing ? (
            <Button variant="outline" onClick={save} disabled={busy !== null}>
              {busy === "save" ? t("ling.saving") : t("ling.save")}
            </Button>
          ) : (
            <Button variant="outline" onClick={() => setEditing(true)} disabled={busy !== null}>
              {t("ling.edit")}
            </Button>
          )}
          <Button
            variant="accent"
            onClick={validate}
            disabled={busy !== null || !local.content_ar}
            className={cx(!local.content_ar && "opacity-60")}
          >
            {t("ling.validate")}
          </Button>
        </div>
      )}
    </li>
  );
}
