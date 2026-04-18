"use client";

import { useEffect, useState } from "react";
import { billingApi, getToken, type SubscriptionOut } from "@/lib/api";

export default function BillingPage() {
  const [sub, setSub] = useState<SubscriptionOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    billingApi
      .get(token)
      .then(setSub)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, []);

  async function checkout() {
    const token = getToken();
    if (!token) return;
    try {
      const { url } = await billingApi.checkout(token);
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function portal() {
    const token = getToken();
    if (!token) return;
    try {
      const { url } = await billingApi.portal(token);
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  const hasSub = sub && sub.status !== "none";

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-3xl font-bold">Facturation</h1>

      <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-xl font-semibold">
          Pack Secrétariat — <span className="text-brand">1 490 € HT / an</span>
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          Abonnement annuel, renouvelé automatiquement chaque année. Résiliable
          depuis le portail client à tout moment.
        </p>
        <p className="mt-3 text-slate-400">
          Automatisation emails, comptes-rendus de réunions et agenda.
          Intégration clé en main à Microsoft 365.
        </p>

        {error && <p className="mt-4 text-red-400">{error}</p>}

        {!sub && <p className="mt-4 text-slate-500">Chargement…</p>}

        {sub && (
          <div className="mt-6 space-y-4">
            <div className="flex items-center gap-3">
              <span
                className={`rounded px-2 py-1 text-sm ${
                  sub.status === "active" || sub.status === "trialing"
                    ? "bg-emerald-900/40 text-emerald-400"
                    : sub.status === "past_due"
                      ? "bg-amber-900/40 text-amber-300"
                      : "bg-slate-800 text-slate-300"
                }`}
              >
                {sub.status}
              </span>
              {sub.current_period_end && (
                <span className="text-sm text-slate-400">
                  Prochaine échéance :{" "}
                  {new Date(sub.current_period_end).toLocaleDateString("fr-FR")}
                </span>
              )}
            </div>

            <div className="flex gap-3">
              {!hasSub && (
                <button
                  onClick={checkout}
                  className="rounded-lg bg-brand px-5 py-2.5 font-semibold text-white hover:bg-brand-dark"
                >
                  S'abonner maintenant
                </button>
              )}
              {hasSub && (
                <button
                  onClick={portal}
                  className="rounded-lg border border-slate-700 px-5 py-2.5 font-semibold text-slate-200 hover:bg-slate-800"
                >
                  Gérer l'abonnement
                </button>
              )}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
