import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://secretary.meoxa.app";
const PLAUSIBLE_DOMAIN = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
// Permet de pointer vers une instance Plausible self-hosted si besoin.
const PLAUSIBLE_SRC =
  process.env.NEXT_PUBLIC_PLAUSIBLE_SRC ?? "https://plausible.io/js/script.js";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Secretary — Secrétariat automatique Microsoft 365 | Meoxa",
    template: "%s | Secretary by Meoxa",
  },
  description:
    "Secretary, l'application éditée par Meoxa, automatise ton secrétariat dans Microsoft 365 : brouillons d'emails, comptes-rendus de réunions Teams, agenda. 1 490 € HT / an.",
  keywords: [
    "secrétariat automatique",
    "Microsoft 365",
    "Outlook",
    "Teams",
    "compte-rendu réunion",
    "IA Claude",
    "PME",
    "France",
    "RGPD",
  ],
  authors: [{ name: "Meoxa" }],
  creator: "Meoxa",
  publisher: "Meoxa",
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: SITE_URL,
    siteName: "Secretary by Meoxa",
    title: "Secretary — Secrétariat automatique Microsoft 365",
    description:
      "L'application Secretary automatise brouillons d'emails, comptes-rendus Teams et agenda dans Microsoft 365.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Secretary — Secrétariat automatique Microsoft 365",
    description:
      "L'application Secretary automatise brouillons d'emails, comptes-rendus Teams et agenda dans Microsoft 365.",
  },
};

export const viewport: Viewport = {
  themeColor: "#0ea5e9",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>
        {children}
        {/* Analytics Plausible — chargée uniquement si NEXT_PUBLIC_PLAUSIBLE_DOMAIN est défini */}
        {PLAUSIBLE_DOMAIN && (
          <Script
            defer
            data-domain={PLAUSIBLE_DOMAIN}
            src={PLAUSIBLE_SRC}
            strategy="afterInteractive"
          />
        )}
      </body>
    </html>
  );
}
