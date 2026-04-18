"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MsStatusBanner } from "@/components/MsStatusBanner";
import { authApi, dashboardApi, getToken, tenantApi } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<Awaited<ReturnType<typeof authApi.me>> | null>(null);
  const [dash, setDash] = useState<Awaited<ReturnType<typeof dashboardApi.get>> | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const [profile, onboarding] = await Promise.all([
          authApi.me(token),
          tenantApi.onboardingStatus(token).catch(() => null),
        ]);
        setMe(profile);
        if (
          onboarding &&
          !onboarding.completed &&
          (profile.role === "owner" || profile.role === "admin")
        ) {
          router.replace("/app/onboarding");
          return;
        }
        dashboardApi.get(token).then(setDash).catch(() => setDash(null));
      } catch {
        // ignore
      }
    })();
  }, [router]);

  const isAdmin = me?.role === "owner" || me?.role === "admin";

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Tableau de bord</h1>
          <p className="mt-2 text-slate-400">
            Vue d'ensemble des emails à traiter, prochaines réunions et CR récents.
          </p>
        </div>
        <nav className="flex flex-wrap gap-2 text-sm">
          <Link
            href="/app/security"
            className="rounded-lg border border-slate-700 px-3 py-2 hover:bg-slate-800"
          >
            Sécurité
          </Link>
          {isAdmin && (
            <>
              <Link
                href="/app/team"
                className="rounded-lg border border-slate-700 px-3 py-2 hover:bg-slate-800"
              >
                Équipe
              </Link>
              <Link
                href="/app/organization"
                className="rounded-lg border border-slate-700 px-3 py-2 hover:bg-slate-800"
              >
                Organisation
              </Link>
              <Link
                href="/app/billing"
                className="rounded-lg border border-slate-700 px-3 py-2 hover:bg-slate-800"
              >
                Facturation
              </Link>
              <Link
                href="/app/admin/settings"
                className="rounded-lg border border-slate-700 px-3 py-2 hover:bg-slate-800"
              >
                Paramètres org.
              </Link>
            </>
          )}
          {me?.is_superadmin && (
            <>
              <Link
                href="/app/admin/dashboard"
                className="rounded-lg border border-sky-700 bg-sky-900/30 px-3 py-2 text-sky-200 hover:bg-sky-900/50"
              >
                Dashboard plateforme
              </Link>
              <Link
                href="/app/admin/platform"
                className="rounded-lg border border-sky-700 bg-sky-900/30 px-3 py-2 text-sky-200 hover:bg-sky-900/50"
              >
                Config plateforme
              </Link>
            </>
          )}
        </nav>
      </div>
      <MsStatusBanner />

      <div className="mt-8 grid gap-4 md:grid-cols-4">
        <Card
          title="Brouillons à relire"
          value={fmt(dash?.stats.emails_to_review)}
          href="/app/emails"
        />
        <Card
          title="Réunions à venir"
          value={fmt(dash?.stats.meetings_upcoming)}
          href="/app/meetings"
        />
        <Card
          title="CR prêts"
          value={fmt(dash?.stats.crs_ready)}
          href="/app/meetings"
        />
        <Card
          title="Coût IA ce mois"
          value={dash ? `$${dash.stats.llm_cost_usd_mtd.toFixed(2)}` : "—"}
        />
      </div>

      <div className="mt-10 grid gap-6 md:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Derniers emails</h2>
            <Link href="/app/emails" className="text-xs text-slate-400 hover:text-slate-200">
              Tout voir →
            </Link>
          </div>
          <ul className="mt-3 space-y-2 text-sm">
            {!dash && <li className="text-slate-500">Chargement…</li>}
            {dash?.recent_emails.length === 0 && (
              <li className="text-slate-500">Aucun email pour le moment.</li>
            )}
            {dash?.recent_emails.map((e) => (
              <li key={e.id}>
                <Link
                  href={`/app/emails/${e.id}`}
                  className="flex items-center justify-between rounded px-2 py-2 hover:bg-slate-800/50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold">{e.subject}</div>
                    <div className="truncate text-xs text-slate-400">{e.from_address}</div>
                  </div>
                  <StatusBadge status={e.status} />
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Réunions récentes</h2>
            <Link href="/app/meetings" className="text-xs text-slate-400 hover:text-slate-200">
              Tout voir →
            </Link>
          </div>
          <ul className="mt-3 space-y-2 text-sm">
            {!dash && <li className="text-slate-500">Chargement…</li>}
            {dash?.recent_meetings.length === 0 && (
              <li className="text-slate-500">Aucune réunion pour le moment.</li>
            )}
            {dash?.recent_meetings.map((m) => (
              <li key={m.id}>
                <Link
                  href={`/app/meetings/${m.id}`}
                  className="flex items-center justify-between rounded px-2 py-2 hover:bg-slate-800/50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold">{m.title}</div>
                    <div className="text-xs text-slate-400">
                      {new Date(m.starts_at).toLocaleString("fr-FR")}
                    </div>
                  </div>
                  {m.has_summary ? (
                    <span className="rounded bg-emerald-900/40 px-2 py-1 text-xs text-emerald-400">
                      CR prêt
                    </span>
                  ) : (
                    <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">
                      {m.status}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}

function Card({ title, value, href }: { title: string; value: string; href?: string }) {
  const content = (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 hover:border-slate-700">
      <div className="text-sm text-slate-400">{title}</div>
      <div className="mt-2 text-3xl font-bold">{value}</div>
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "drafted"
      ? "bg-sky-900/40 text-sky-300"
      : status === "sent"
        ? "bg-emerald-900/40 text-emerald-400"
        : status === "ignored"
          ? "bg-slate-800 text-slate-500"
          : "bg-amber-900/40 text-amber-300";
  return <span className={`rounded px-2 py-1 text-xs ${cls}`}>{status}</span>;
}

function fmt(n: number | undefined): string {
  return typeof n === "number" ? String(n) : "—";
}
