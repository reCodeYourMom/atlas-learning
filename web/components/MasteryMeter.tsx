"use client";

import { useEffect, useState } from "react";
import { useLang } from "@/components/LanguageProvider";
import { cx } from "@/components/ui";
import type { MasteryMove } from "@/lib/types";
import { abilityToPct } from "@/lib/mastery";

/**
 * L'estimation de maîtrise qui BOUGE, après chaque réponse.
 *
 * C'est le seul endroit du produit où l'adaptativité devient visible : ailleurs on montre
 * un état, ici on montre une RÉVISION. La barre part de la position d'avant puis glisse
 * vers celle d'après — voir le trajet est tout l'intérêt ; afficher directement la valeur
 * finale ne dirait rien de plus qu'un chiffre.
 *
 * Le repère de maîtrise est tracé en clair : sans lui, « ça monte » n'a pas d'échelle.
 */
export function MasteryMeter({ move }: { move: MasteryMove }) {
  const { t, lang } = useLang();
  const [arrived, setArrived] = useState(false);

  const from = abilityToPct(move.before.elo);
  const to = abilityToPct(move.after.elo);
  const threshold = abilityToPct(1500); // seuil de maîtrise, même échelle que la barre

  // Deux frames de latence : le navigateur doit peindre la position de DÉPART avant la
  // transition, sinon la barre apparaît déjà arrivée et le mouvement est invisible.
  useEffect(() => {
    setArrived(false);
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setArrived(true)));
    return () => cancelAnimationFrame(id);
  }, [move.competency_id, move.after.elo, move.before.elo]);

  const label = (lang === "ar" ? move.label_ar : move.label_en) ?? "";
  const rising = move.delta_elo > 0.5;
  const falling = move.delta_elo < -0.5;
  const verdict = rising ? t("mastery.up") : falling ? t("mastery.down") : t("mastery.steady");

  return (
    <div className="rounded-2xl border border-sand-200 bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="text-xs font-medium uppercase tracking-wide text-sand-400">
          {t("mastery.measuring")}
        </p>
        <p
          className={cx(
            "num text-sm font-semibold",
            rising ? "text-mastered" : falling ? "text-gold-700" : "text-sand-400",
          )}
        >
          {move.delta_elo > 0 ? "+" : ""}
          {move.delta_elo.toFixed(0)}
        </p>
      </div>
      <p className="mt-0.5 font-medium leading-snug text-sand-800">{label}</p>

      {/* La barre. `arrived` bascule la largeur : c'est la transition CSS qui fait le trajet. */}
      <div className="relative mt-3 h-3 overflow-hidden rounded-full bg-sand-100">
        <div
          className={cx(
            "h-full rounded-full transition-[width] duration-700 ease-out motion-reduce:transition-none",
            move.after.mastered ? "bg-mastered" : "bg-progress",
          )}
          style={{ width: `${arrived ? to : from}%` }}
        />
        {/* Repère de maîtrise : donne son échelle au mouvement. */}
        <div
          className="absolute inset-y-0 w-px bg-sand-400"
          style={{ insetInlineStart: `${threshold}%` }}
          aria-hidden
        />
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="text-xs text-sand-500">
          {verdict}
          {move.crossed_mastery && (
            <span className="num ms-2 rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-800">
              {t("mastery.crossed")}
            </span>
          )}
        </p>
        {/* La confiance dit à l'interlocuteur que le système sait ce qu'il ne sait pas encore. */}
        <p className="num text-xs text-sand-400">
          {t("mastery.confidence")} {Math.round(move.after.confidence * 100)}% ·{" "}
          {move.after.n_direct} {t("mastery.answers")}
        </p>
      </div>
    </div>
  );
}
