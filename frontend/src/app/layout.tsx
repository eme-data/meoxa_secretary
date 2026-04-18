import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Secretary — Secrétariat automatique Microsoft 365 | Meoxa",
  description:
    "Secretary, l'application éditée par Meoxa, automatise ton secrétariat dans Microsoft 365 : brouillons d'emails, comptes-rendus de réunions Teams, agenda. 1 490 € HT / an.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
