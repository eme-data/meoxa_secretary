"use client";

import { useEffect, useState } from "react";
import { getToken, integrationsApi, type MsIntegrationStatus } from "@/lib/api";

export function MsStatusBanner() {
  const [status, setStatus] = useState<MsIntegrationStatus | null>(null);
  const [reconnecting, setReconnecting] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    integrationsApi.microsoftStatus(token).then(setStatus).catch(() => setStatus(null));
  }, []);

  if (!status || status.healthy) return null;

  async function reconnect() {
    const token = getToken();
    if (!token) return;
    setReconnecting(true);
    try {
      const { authorize_url } = await integrationsApi.microsoftAuthorize(token);
      window.location.href = authorize_url;
    } catch (e) {
      setReconnecting(false);
      alert(
        e instanceof Error ? `Reconnexion Microsoft impossible : ${e.message}` : "Erreur inconnue",
      );
    }
  }

  return (
    <div className="mx-auto mt-4 max-w-5xl rounded-lg border border-amber-800 bg-amber-900/30 p-3 text-sm text-amber-200">
      <strong>Connexion Microsoft 365 à vérifier.</strong>{" "}
      {status.last_error
        ? status.last_error
        : status.expired
          ? "Les tokens ont expiré — reconnecte-toi pour reprendre le traitement automatique."
          : "Intégration indisponible."}{" "}
      <button
        onClick={reconnect}
        disabled={reconnecting}
        className="font-semibold underline hover:text-amber-100 disabled:opacity-60"
      >
        {reconnecting ? "Redirection…" : "Reconnecter Microsoft"}
      </button>
    </div>
  );
}
