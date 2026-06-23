// Primitives de maîtrise réutilisées partout (Brief §10 — l'indicateur est LA primitive).
import type { CompetencyMastery } from "./types";
import type { Lang } from "./i18n";

export const MASTERY_ELO = 1500; // miroir de src/restitution/diagnosis.py
export const CONFIDENCE_THRESHOLD = 0.5;

export type MasteryState = "mastered" | "progress" | "unmeasured";

export function masteryState(c: Pick<CompetencyMastery, "measured" | "mastered">): MasteryState {
  if (!c.measured) return "unmeasured";
  return c.mastered ? "mastered" : "progress";
}

// Couleurs sémantiques — vert maîtrisé, ambre en cours, gris non mesuré. Jamais de rouge pour une lacune.
export const STATE_STYLE: Record<MasteryState, { dot: string; bar: string; text: string; chip: string }> = {
  mastered: {
    dot: "bg-mastered",
    bar: "bg-mastered",
    text: "text-mastered",
    chip: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  },
  progress: {
    dot: "bg-progress",
    bar: "bg-progress",
    text: "text-gold-700",
    chip: "bg-gold-50 text-gold-700 ring-gold-200",
  },
  unmeasured: {
    dot: "bg-unmeasured",
    bar: "bg-unmeasured",
    text: "text-sand-500",
    chip: "bg-sand-100 text-sand-600 ring-sand-200",
  },
};

// Position 0..100 d'une ability sur l'échelle d'ancrage (G2≈1000 → G6≈2100).
export function abilityToPct(elo: number): number {
  return Math.max(4, Math.min(100, Math.round(((elo - 1000) / (2100 - 1000)) * 100)));
}

// Table d'ancrage (miroir de src/restitution/scale.py DEFAULT_ANCHORS) — niveau lisible.
const ANCHORS: { elo: number; level: string }[] = [
  { elo: 1000, level: "G2" },
  { elo: 1300, level: "G3" },
  { elo: 1500, level: "G4" },
  { elo: 1800, level: "G5" },
  { elo: 2100, level: "G6" },
];

export function eloToLevel(elo: number | null): string {
  if (elo == null) return "—";
  let chosen = ANCHORS[0].level;
  for (const a of ANCHORS) if (elo >= a.elo) chosen = a.level;
  return chosen;
}

// Confiance faible → on l'affiche honnêtement (Brief §2). Renvoie true si « estimé ».
export function isEstimated(confidence: number): boolean {
  return confidence < CONFIDENCE_THRESHOLD;
}

export function label(c: { label_en: string; label_ar: string }, lang: Lang): string {
  return lang === "ar" ? c.label_ar : c.label_en;
}
