"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getToken, integrationsApi, type MsIntegrationStatus } from "@/lib/api";

export function MsStatusBanner() {
  const [status, setStatus] = useState<MsIntegrationStatus | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    integrationsApi.microsoftStatus(token).then(setStatus).catch(() => setStatus(null));
  }, []);

  if (!status || status.healthy) return null;

  return (
    <div className="mx-auto mt-4 max-w-5xl rounded-lg border border-amber-800 bg-amber-900/30 p-3 text-sm text-amber-200">
      <strong>Connexion Microsoft 365 à vérifier.</strong>{" "}
      {status.last_error
        ? status.last_error
        : status.expired
          ? "Les tokens ont expiré — reconnecte-toi pour reprendre le traitement automatique."
          : "Intégration indisponible."}{" "}
      <Link href="/app/onboarding" className="underline font-semibold">
        Reconnecter Microsoft
      </Link>
    </div>
  );
}
