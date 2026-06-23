"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { useLang } from "@/components/LanguageProvider";
import { Button } from "@/components/ui";
import { Logo } from "@/components/AppShell";
import { api, ApiError, setToken } from "@/lib/api";

type Enroll = { setupToken: string; secret: string; otpauth_uri: string };

const PROVIDER_LABEL: Record<string, string> = {
  google: "Google",
  microsoft: "Microsoft",
  generic: "SSO",
};

export default function LoginPage() {
  const { t, toggle, lang } = useLang();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfa, setMfa] = useState("");
  const [needMfa, setNeedMfa] = useState(false);
  const [providers, setProviders] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Boutons SSO selon les providers activés côté serveur.
    api.authProviders().then((r) => setProviders(r.providers)).catch(() => setProviders([]));
    // Erreur renvoyée par le flux SSO (?sso_error=…).
    const sso = new URLSearchParams(window.location.search).get("sso_error");
    if (sso) setError(t("login.sso.error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [busy, setBusy] = useState(false);
  const [enroll, setEnroll] = useState<Enroll | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(email, password, mfa || undefined);
      if ("mfa_setup_required" in res) {
        // 1er login staff : on bascule sur l'écran d'enrôlement TOTP.
        const { secret, otpauth_uri } = await api.mfaEnroll(res.setup_token);
        setEnroll({ setupToken: res.setup_token, secret, otpauth_uri });
        return;
      }
      setToken(res.token);
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError && err.detail === "mfa_required") {
        setNeedMfa(true);
        setError(t("login.mfa.required"));
      } else {
        setError(t("login.error"));
      }
    } finally {
      setBusy(false);
    }
  }

  if (enroll) {
    return (
      <EnrollScreen
        enroll={enroll}
        onDone={(token) => {
          setToken(token);
          router.replace("/");
        }}
      />
    );
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Panneau marque — institutionnel, calme, premium. */}
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

      {/* Formulaire. */}
      <div className="flex flex-col items-center justify-center bg-sand-50 px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-sand-800">{t("login.title")}</h2>
            <button onClick={toggle} className="text-sm font-medium text-brand-600 hover:underline">
              {lang === "en" ? "العربية" : "English"}
            </button>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <Field label={t("login.email")}>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400"
                autoComplete="username"
              />
            </Field>
            <Field label={t("login.password")}>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400"
                autoComplete="current-password"
              />
            </Field>
            {needMfa && (
              <Field label={t("login.mfa")} hint={t("login.mfa.hint")}>
                <input
                  inputMode="numeric"
                  value={mfa}
                  onChange={(e) => setMfa(e.target.value)}
                  className="w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400"
                  data-ltr
                />
              </Field>
            )}

            {error && <p className="text-sm text-danger">{error}</p>}

            <Button type="submit" disabled={busy} className="w-full">
              {t("login.submit")}
            </Button>
          </form>

          {providers.length > 0 && (
            <div className="mt-6">
              <div className="mb-3 flex items-center gap-3 text-xs text-sand-400">
                <span className="h-px flex-1 bg-sand-200" />
                {t("login.sso.or")}
                <span className="h-px flex-1 bg-sand-200" />
              </div>
              <div className="space-y-2">
                {providers.map((key) => (
                  // Navigation pleine page (le start redirige vers l'IdP) — pas un fetch.
                  <a
                    key={key}
                    href={`/api/oauth/${key}/start`}
                    className="block w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-center text-sm font-medium text-sand-700 hover:border-brand-400 hover:bg-sand-50"
                  >
                    {t("login.sso.with")} {PROVIDER_LABEL[key] ?? key}
                  </a>
                ))}
              </div>
            </div>
          )}

          <p className="mt-6 text-center text-sm text-sand-500">
            <a href="/parent" className="font-medium text-brand-600 hover:underline">
              {t("login.parent")}
            </a>
          </p>

          <div className="mt-8 rounded-xl border border-sand-200 bg-white p-4 text-xs text-sand-500">
            <p className="mb-1 font-semibold text-sand-600">{t("login.demo")}</p>
            <ul className="space-y-0.5" data-ltr>
              <li>prof@demo.atlas · demo1234 (MFA)</li>
              <li>admin@demo.atlas · demo1234 (MFA)</li>
              <li>eleve1@demo.atlas · demo1234</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-sand-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-sand-400">{hint}</span>}
    </label>
  );
}

function EnrollScreen({ enroll, onDone }: { enroll: Enroll; onDone: (token: string) => void }) {
  const { t } = useLang();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { token } = await api.mfaConfirm(enroll.setupToken, code);
      onDone(token);
    } catch {
      setError(t("mfa.setup.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-sand-50 px-6 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <Logo />
          <span className="text-lg font-semibold text-sand-800">{t("mfa.setup.title")}</span>
        </div>
        <p className="mb-4 text-sm text-sand-600">{t("mfa.setup.intro")}</p>

        <div className="mb-4 flex justify-center rounded-xl border border-sand-200 bg-white p-5">
          <QRCodeSVG value={enroll.otpauth_uri} size={176} />
        </div>

        <p className="mb-1 text-xs text-sand-500">{t("mfa.setup.manual")}</p>
        <code
          className="mb-5 block break-all rounded-lg bg-sand-100 px-3 py-2 text-xs text-sand-700"
          data-ltr
        >
          {enroll.secret}
        </code>

        <form onSubmit={confirm} className="space-y-4">
          <Field label={t("mfa.setup.code")}>
            <input
              inputMode="numeric"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full rounded-xl border border-sand-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-brand-400"
              data-ltr
            />
          </Field>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" disabled={busy} className="w-full">
            {t("mfa.setup.confirm")}
          </Button>
        </form>
      </div>
    </div>
  );
}
