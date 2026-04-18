"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { adminDashboardApi, authApi, getToken, type TenantSummary } from "@/lib/api";

export default function SuperAdminDashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<{
    generated_at: string;
    totals: Record<string, number>;
    tenants: TenantSummary[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const me = await authApi.me(token);
        if (!me.is_superadmin) {
          setError("Accès réservé au super-admin de la plateforme.");
          return;
        }
        setData(await adminDashboardApi.tenants(token));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erreur");
      }
    })();
  }, [router]);

  if (error) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-10">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }
  if (!data) return <main className="mx-auto max-w-5xl px-6 py-10 text-slate-500">Chargement…</main>;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard plateforme</h1>
          <p className="mt-1 text-sm text-slate-400">
            Généré le {new Date(data.generated_at).toLocaleString("fr-FR")}
          </p>
        </div>
        <Link
          href="/app/admin/platform"
          className="rounded-lg border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800"
        >
          Config plateforme
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <Tile label="Tenants" value={fmt(data.totals.tenants)} />
        <Tile label="Abos actifs" value={fmt(data.totals.active_subscriptions)} />
        <Tile
          label="Coût LLM (mois)"
          value={`$${data.totals.llm_cost_usd_mtd.toFixed(2)}`}
        />
      </div>

      <section className="mt-10">
        <h2 className="text-xl font-semibold">Tenants</h2>
        <div className="mt-4 overflow-x-auto rounded-xl border border-slate-800">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-900/60 text-left text-slate-400">
              <tr>
                <th className="px-4 py-2">Nom</th>
                <th className="px-4 py-2">Membres</th>
                <th className="px-4 py-2">Abonnement</th>
                <th className="px-4 py-2">Onboardé</th>
                <th className="px-4 py-2">Dernière activité</th>
                <th className="px-4 py-2">Coût LLM (mois)</th>
                <th className="px-4 py-2">Appels</th>
              </tr>
            </thead>
            <tbody>
              {data.tenants.map((t) => (
                <tr key={t.id} className="border-t border-slate-800">
                  <td className="px-4 py-2">
                    <div className="font-semibold">{t.name}</div>
                    <div className="font-mono text-xs text-slate-500">{t.slug}</div>
                  </td>
                  <td className="px-4 py-2">{t.members_count}</td>
                  <td className="px-4 py-2">
                    <SubscriptionBadge status={t.subscription_status} />
                  </td>
                  <td className="px-4 py-2">
                    {t.onboarded_at ? "✓" : <span className="text-amber-400">en cours</span>}
                  </td>
                  <td className="px-4 py-2 text-slate-400">
                    {t.last_activity_at
                      ? new Date(t.last_activity_at).toLocaleDateString("fr-FR")
                      : "—"}
                  </td>
                  <td className="px-4 py-2 font-mono">
                    ${t.llm_cost_usd_mtd.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-slate-400">{t.llm_calls_mtd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
      <div className="text-sm text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-bold">{value}</div>
    </div>
  );
}

function SubscriptionBadge({ status }: { status: string }) {
  const cls =
    status === "active" || status === "trialing"
      ? "bg-emerald-900/40 text-emerald-400"
      : status === "past_due"
        ? "bg-amber-900/40 text-amber-300"
        : "bg-slate-800 text-slate-400";
  return <span className={`rounded px-2 py-1 text-xs ${cls}`}>{status}</span>;
}

function fmt(n: number): string {
  return Number.isFinite(n) ? String(Math.round(n)) : "—";
}
