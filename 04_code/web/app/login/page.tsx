"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLang } from "@/components/LanguageProvider";
import { Logo } from "@/components/AppShell";
import { api, setToken } from "@/lib/api";

// Auth = SSO/OIDC uniquement (plus de mot de passe : cf. 0013_drop_direct_auth). Les boutons
// reflètent les providers activés côté serveur (/auth/providers). En prod : Keycloak (TOTP).
const PROVIDER_LABEL: Record<string, string> = {
  google: "Google",
  microsoft: "Microsoft",
  uaepass: "UAE PASS",
  generic: "Atlas",
};

export default function LoginPage() {
  const { t, toggle, lang } = useLang();
  const [providers, setProviders] = useState<string[] | null>(null);
  const [demoLogin, setDemoLogin] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .authProviders()
      .then((r) => {
        setProviders(r.providers);
        setDemoLogin(r.demo_login);
      })
      .catch(() => setProviders([]));
    if (new URLSearchParams(window.location.search).get("sso_error")) setError(t("login.sso.error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Panneau marque. */}
      <aside className="relative hidden flex-col justify-between bg-brand-800 p-10 text-white lg:flex">
        <div className="flex items-center gap-2">
          <Logo />
          <span className="text-lg font-semibold">{t("app.name")}</span>
        </div>
        <div className="max-w-md">
          <h1 className="text-3xl font-semibold leading-tight">{t("app.tagline")}</h1>
          <p className="mt-4 text-brand-100/80">
            {lang === "ar"
              ? "نُظهر مسار تعلّم الطفل — قابلًا للقياس والإثبات — مهارةً مهارة."
              : "We make a child's learning trajectory visible and provable — skill by skill."}
          </p>
        </div>
        <div className="h-1 w-24 rounded-full bg-gold-400" />
      </aside>

      {/* Connexion. */}
      <div className="flex flex-col items-center justify-center bg-sand-50 px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-sand-800">{t("login.title")}</h2>
            <button onClick={toggle} className="text-sm font-medium text-brand-600 hover:underline">
              {lang === "en" ? "العربية" : "English"}
            </button>
          </div>

          {error && <p className="mb-4 text-sm text-danger">{error}</p>}

          {/* Formulaire de démonstration : présent uniquement si le serveur l'annonce
              (DEMO_LOGIN_PASSWORD posé, hors production). */}
          {demoLogin && <DemoLoginForm onError={setError} />}

          {providers === null ? (
            <p className="text-sm text-sand-500">{t("common.loading")}</p>
          ) : providers.length === 0 ? (
            demoLogin ? null : (
              <p className="rounded-xl border border-sand-200 bg-white p-4 text-sm text-sand-500">
                {t("login.noprovider")}
              </p>
            )
          ) : (
            <div className="space-y-2">
              {providers.map((key) => (
                // Navigation pleine page : /start redirige vers l'IdP (Keycloak → TOTP).
                <a
                  key={key}
                  href={`/api/oauth/${key}/start`}
                  className="block w-full rounded-xl bg-brand-600 px-3.5 py-3 text-center text-sm font-semibold text-white hover:bg-brand-700"
                >
                  {t("login.sso.with")} {PROVIDER_LABEL[key] ?? key}
                </a>
              ))}
            </div>
          )}

          <p className="mt-6 text-center text-sm text-sand-500">
            <a href="/parent" className="font-medium text-brand-600 hover:underline">
              {t("login.parent")}
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}


/** Connexion de démonstration : un compte du jeu de démo + le mot de passe partagé. */
function DemoLoginForm({ onError }: { onError: (m: string | null) => void }) {
  const { t } = useLang();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    onError(null);
    try {
      const { token } = await api.demoLogin(email, password);
      setToken(token);
      // `replace` : la page de connexion ne doit pas rester dans l'historique.
      router.replace("/");
    } catch {
      onError(t("login.demo.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-2.5">
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder={t("login.demo.email")}
        autoComplete="username"
        className="w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400"
        data-ltr
      />
      <input
        type="password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder={t("login.demo.password")}
        autoComplete="current-password"
        className="w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400"
        data-ltr
      />
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-xl bg-brand-600 px-3.5 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? "…" : t("login.demo.submit")}
      </button>
    </form>
  );
}
