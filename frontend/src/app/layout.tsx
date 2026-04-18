import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "meoxa_secretary",
  description: "Automatisation secrétariat : emails, comptes-rendus de réunions, agenda.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
