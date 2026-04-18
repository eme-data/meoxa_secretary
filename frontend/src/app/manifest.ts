import type { MetadataRoute } from "next";

// PWA manifest — permet l'installation sur téléphone/desktop ("Ajouter à l'écran d'accueil")
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Secretary by Meoxa",
    short_name: "Secretary",
    description:
      "Secrétariat automatique Microsoft 365 — brouillons d'emails, comptes-rendus Teams, agenda.",
    start_url: "/app",
    display: "standalone",
    background_color: "#020617",
    theme_color: "#0ea5e9",
    lang: "fr",
    categories: ["productivity", "business"],
    icons: [
      {
        src: "/icon",
        sizes: "32x32",
        type: "image/png",
      },
      {
        src: "/apple-icon",
        sizes: "180x180",
        type: "image/png",
      },
      {
        src: "/apple-icon",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/apple-icon",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
