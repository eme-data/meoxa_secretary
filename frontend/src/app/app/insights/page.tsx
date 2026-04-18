"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getToken, insightsApi, type InsightsResponse } from "@/lib/api";

export default function InsightsPage() {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    insightsApi
      .get(token)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, []);

  if (error) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10 text-slate-500">Chargement…</main>
    );
  }

  const maxActivity =
    Math.max(
      ...data.last_7_days.map((d) => d.drafts + d.crs * 5),
      1,
    );

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-bold">Ta valeur Secretary</h1>
      <p className="mt-2 text-slate-400">
        Ce que Secretary t'a fait gagner depuis le début du mois — mis à jour en direct.
      </p>

      <section className="mt-8 rounded-2xl border border-sky-700/30 bg-gradient-to-br from-sky-900/20 to-slate-900/60 p-8">
        <div className="text-sm uppercase tracking-wider text-sky-300">
          Temps restitué ce mois
        </div>
        <div className="mt-2 text-5xl font-bold text-white md:text-6xl">
          {data.time_saved_label}
        </div>
        <p className="mt-3 text-sm text-slate-400">
          Secretary a produit{" "}
          <strong className="text-white">{data.drafts_generated}</strong> brouillons
          d'emails et <strong className="text-white">{data.crs_generated}</strong>{" "}
          comptes-rendus de réunions. En moyenne, 2 minutes gagnées par brouillon et
          40 minutes par CR (hypothèses prudentes).
        </p>
      </section>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <Tile
          label="Brouillons produits"
          value={data.drafts_generated.toString()}
          detail="dans Outlook ce mois"
        />
        <Tile
          label="CR générés"
          value={data.crs_generated.toString()}
          detail="envoyés par mail"
        />
        <Tile
          label="Coût IA ce mois"
          value={`$${data.llm_cost_usd.toFixed(2)}`}
          detail={`${data.llm_calls} appels Claude`}
        />
      </div>

      <section className="mt-10 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold">Activité des 7 derniers jours</h2>
        <p className="text-xs text-slate-500">
          Somme des brouillons + CR (pondérés). Plus la barre est haute, plus Secretary a
          travaillé ce jour-là.
        </p>
        <div className="mt-6 flex h-40 items-end gap-2">
          {data.last_7_days.map((d) => {
            const total = d.drafts + d.crs * 5;
            const h = Math.max(4, (total / maxActivity) * 100);
            const day = new Date(d.date).toLocaleDateString("fr-FR", { weekday: "short" });
            return (
              <div key={d.date} className="flex flex-1 flex-col items-center gap-2">
                <div
                  className="w-full rounded-t bg-gradient-to-t from-sky-700 to-sky-400"
                  style={{ height: `${h}%` }}
                  title={`${d.drafts} brouillons · ${d.crs} CR · $${d.llm_cost_usd.toFixed(3)}`}
                />
                <div className="text-xs text-slate-500">{day}</div>
                <div className="text-xs font-mono text-slate-400">
                  {d.drafts + d.crs}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mt-10 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold">Prochaines étapes</h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-300">
          {data.drafts_generated === 0 && (
            <li>
              ·{" "}
              <Link href="/app/onboarding" className="text-sky-400 hover:underline">
                Termine ton onboarding
              </Link>{" "}
              pour commencer à recevoir des brouillons automatiques.
            </li>
          )}
          {data.drafts_generated > 0 && (
            <li>
              · Vérifie tes{" "}
              <Link href="/app/emails" className="text-sky-400 hover:underline">
                brouillons en attente
              </Link>{" "}
              dans Outlook ou depuis l'interface.
            </li>
          )}
          {data.crs_generated > 0 && (
            <li>
              · Consulte tes{" "}
              <Link href="/app/meetings" className="text-sky-400 hover:underline">
                comptes-rendus
              </Link>{" "}
              et les actions extraites vers Planner.
            </li>
          )}
          <li>
            · Invite ton équipe depuis{" "}
            <Link href="/app/team" className="text-sky-400 hover:underline">
              /app/team
            </Link>{" "}
            — les utilisateurs sont illimités dans ton abonnement.
          </li>
        </ul>
      </section>
    </main>
  );
}

function Tile({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
      <div className="text-sm text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-bold">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{detail}</div>
    </div>
  );
}
