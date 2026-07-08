"use client";

import { useEffect, useState } from "react";
import { useLang } from "@/components/LanguageProvider";
import { Button } from "@/components/ui";
import { Logo } from "@/components/AppShell";
import { api } from "@/lib/api";

// Accès linguiste sans mot de passe (staff Atlas global) : on saisit son email → lien
// magique single-use. Même patron que /parent et /admin (super-admin).
export default function LinguistRequestPage() {
  const { t, lang, toggle } = useLang();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Codes d'erreur renvoyés par le GET du lien magique (linguist_error=used|invalid|forbidden).
    if (new URLSearchParams(window.location.search).get("linguist_error")) {
      setError(t("parent.login.expired"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.linguistRequestLink(email);
      setSent(true);
    } catch {
      setSent(true); // réponse constante : on ne révèle jamais si l'email est linguiste
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-sand-50 px-6 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Logo />
            <span className="text-lg font-semibold text-sand-800">{t("app.name")}</span>
          </div>
          <button onClick={toggle} className="text-sm font-medium text-brand-600 hover:underline">
            {lang === "en" ? "العربية" : "English"}
          </button>
        </div>

        {sent ? (
          <div className="rounded-xl border border-sand-200 bg-white p-6 text-sm text-sand-700">
            <p className="font-medium">{t("ling.login.sent.title")}</p>
            <p className="mt-1 text-sand-500">{t("ling.login.sent.body")}</p>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <h1 className="text-xl font-semibold text-sand-800">{t("ling.login.title")}</h1>
            <p className="text-sm text-sand-500">{t("ling.login.intro")}</p>
            {error && <p className="text-sm text-danger">{error}</p>}
            <input
              type="email"
              required
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              placeholder={t("login.email")}
              className="w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400"
              autoComplete="email"
            />
            <Button type="submit" disabled={busy} className="w-full">
              {t("ling.login.submit")}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
