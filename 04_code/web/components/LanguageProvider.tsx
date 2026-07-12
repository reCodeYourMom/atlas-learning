"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { DictKey, Lang, translate } from "@/lib/i18n";

interface LangCtx {
  lang: Lang;
  dir: "rtl" | "ltr";
  setLang: (l: Lang) => void;
  toggle: () => void;
  t: (key: DictKey) => string;
}

const Ctx = createContext<LangCtx | null>(null);
const STORAGE_KEY = "atlas.lang";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  // Garde-fou : on ne persiste JAMAIS avant d'avoir restauré la préférence,
  // sinon le double-montage de StrictMode écrase la valeur sauvegardée par le défaut "en".
  const [hydrated, setHydrated] = useState(false);

  // Restaure la préférence au montage (défaut EN pour matcher le rendu SSR).
  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY) as Lang | null;
    if (saved === "ar" || saved === "en") setLangState(saved);
    setHydrated(true);
  }, []);

  // Applique lang + dir sur <html> et persiste — uniquement APRÈS restauration.
  useEffect(() => {
    if (!hydrated) return;
    const el = document.documentElement;
    el.lang = lang;
    el.dir = lang === "ar" ? "rtl" : "ltr";
    window.localStorage.setItem(STORAGE_KEY, lang);
  }, [lang, hydrated]);

  const setLang = useCallback((l: Lang) => setLangState(l), []);
  const toggle = useCallback(() => setLangState((p) => (p === "en" ? "ar" : "en")), []);
  const t = useCallback((key: DictKey) => translate(key, lang), [lang]);

  const dir = lang === "ar" ? "rtl" : "ltr";
  return <Ctx.Provider value={{ lang, dir, setLang, toggle, t }}>{children}</Ctx.Provider>;
}

export function useLang(): LangCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useLang must be used within LanguageProvider");
  return ctx;
}
