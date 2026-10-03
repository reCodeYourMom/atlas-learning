"use client";

import { useLang } from "@/components/LanguageProvider";
import { Logo } from "@/components/AppShell";

// Entrée d'onboarding self-service : l'IT admin lance le Sign-in Google (admin Workspace requis).
export default function OnboardingPage() {
  const { t, lang, toggle } = useLang();
  return (
    <div className="grid min-h-screen place-items-center bg-sand-50 px-6 py-12">
      <div className="w-full max-w-md text-center">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Logo />
            <span className="text-lg font-semibold text-sand-800">{t("app.name")}</span>
          </div>
          <button onClick={toggle} className="text-sm font-medium text-brand-600 hover:underline">
            {lang === "en" ? "العربية" : "English"}
          </button>
        </div>

        <h1 className="text-2xl font-semibold text-sand-800">{t("onboarding.title")}</h1>
        <p className="mx-auto mt-2 max-w-sm text-sm text-sand-500">{t("onboarding.body")}</p>

        {/* Navigation pleine page (redirige vers Google) — pas un fetch. */}
        <a
          href="/api/onboarding/google/start"
          className="mt-6 inline-block rounded-xl bg-brand-600 px-5 py-3 text-sm font-medium text-white hover:bg-brand-700"
        >
          {t("onboarding.cta")}
        </a>
        <p className="mt-3 text-xs text-sand-400">{t("onboarding.note")}</p>
      </div>
    </div>
  );
}
