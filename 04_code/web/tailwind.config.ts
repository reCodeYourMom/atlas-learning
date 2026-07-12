import type { Config } from "tailwindcss";

/**
 * Design tokens — Atlas Learning.
 * Parti pris (Brief §5) : crédible, calme, premium. Bleu profond/teal (institution),
 * accent ambre/or (accomplissement, résonance GCC), neutres chauds, généreux en clair.
 * Sémantiques : vert = maîtrisé, ambre = en cours, gris = non mesuré. Pas de rouge pour les lacunes.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Primaire — bleu profond / teal : confiance, intellect, calme.
        brand: {
          50: "#eef4fb",
          100: "#d6e4f4",
          200: "#aecbe9",
          300: "#7ba9d9",
          400: "#4983c4",
          500: "#2c63a8",
          600: "#1f4d8a",
          700: "#1a3f70",
          800: "#173357",
          900: "#0f2238",
        },
        // Teal secondaire — surfaces fraîches, data calme.
        teal: {
          50: "#edf8f7",
          100: "#cfeceb",
          300: "#7fcfca",
          500: "#2f9c95",
          600: "#1f7d77",
          700: "#185f5b",
        },
        // Accent — ambre / or : accomplissement, CTA clés (un seul focal par écran).
        gold: {
          50: "#fdf6e9",
          100: "#f9e6c2",
          200: "#f1cd86",
          300: "#e8b352",
          400: "#dc9a2c",
          500: "#c47f15",
          600: "#a06410",
          700: "#7c4d10",
        },
        // Neutres chauds — texte et surfaces.
        sand: {
          25: "#fbfaf8",
          50: "#f6f4f0",
          100: "#eceae4",
          200: "#dcd8cf",
          300: "#c2bcb0",
          400: "#9a9489",
          500: "#736e64",
          600: "#54504a",
          700: "#3c3934",
          800: "#272521",
          900: "#16150f",
        },
        // Sémantiques de maîtrise (prudence : pas de rouge pour une lacune).
        mastered: "#2f9e6b",
        progress: "#dc9a2c",
        unmeasured: "#b6b1a6",
        danger: "#b4452f", // erreurs SYSTÈME uniquement
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "system-ui", "sans-serif"],
        ar: ["var(--font-plex-ar)", "var(--font-plex-sans)", "sans-serif"],
      },
      borderRadius: {
        xl: "14px",
        "2xl": "20px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(22,21,15,0.04), 0 4px 16px rgba(22,21,15,0.06)",
        lift: "0 8px 30px rgba(15,34,56,0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
