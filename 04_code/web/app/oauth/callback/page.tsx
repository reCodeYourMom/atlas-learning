"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLang } from "@/components/LanguageProvider";
import { Loading } from "@/components/ui";
import { setToken } from "@/lib/api";

// Retour SSO : l'API redirige ici avec le token de session dans le fragment (#token=…),
// jamais envoyé au serveur ni journalisé. On le stocke puis on rejoint la landing par rôle.
export default function OAuthCallback() {
  const router = useRouter();
  const { t } = useLang();

  useEffect(() => {
    const hash = typeof window !== "undefined" ? window.location.hash : "";
    const token = new URLSearchParams(hash.replace(/^#/, "")).get("token");
    if (token) {
      setToken(token);
      router.replace("/");
    } else {
      router.replace("/login?sso_error=callback");
    }
  }, [router]);

  return (
    <div className="grid min-h-screen place-items-center bg-sand-50">
      <Loading label={t("common.loading")} />
    </div>
  );
}
