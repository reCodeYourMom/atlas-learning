"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLang } from "@/components/LanguageProvider";
import { Button } from "@/components/ui";
import { Logo } from "@/components/AppShell";
import { api, ApiError, setToken } from "@/lib/api";

// Confirmation du lien magique LINGUISTE — même patron anti-préchargement que
// /login/confirm (super-admin) : le GET du lien email ne consomme rien, le clic humain
// POSTe le jeton (fragment #token=…, jamais envoyé aux serveurs) → consommé (single-use).
export default function LinguistConfirmPage() {
  const router = useRouter();
  const { t, lang, toggle } = useLang();
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const hash = typeof window !== "undefined" ? window.location.hash : "";
    const tok = new URLSearchParams(hash.replace(/^#/, "")).get("token");
    if (tok) setLinkToken(tok);
    else router.replace("/linguist/login?linguist_error=invalid");
  }, [router]);

  async function confirm() {
    if (!linkToken || busy) return;
    setBusy(true);
    try {
      const { token } = await api.linguistLoginConfirm(linkToken);
      setToken(token);
      router.replace("/linguist"); // file de validation AR
    } catch (e) {
      // `detail` = code machine (used | invalid | forbidden).
      const code =
        e instanceof ApiError && (e.detail === "invalid" || e.detail === "forbidden")
          ? e.detail
          : "used";
      router.replace(`/linguist/login?linguist_error=${code}`);
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

        <div className="rounded-xl border border-sand-200 bg-white p-6">
          <h1 className="text-xl font-semibold text-sand-800">{t("magic.confirm.title")}</h1>
          <p className="mt-1 text-sm text-sand-500">{t("magic.confirm.body")}</p>
          <Button onClick={confirm} disabled={busy || !linkToken} className="mt-4 w-full">
            {t("magic.confirm.submit")}
          </Button>
        </div>
      </div>
    </div>
  );
}
