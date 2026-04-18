"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  type EmailThreadListItem,
  type EmailUrgency,
  emailsApi,
  getToken,
} from "@/lib/api";

type UrgencyFilter = EmailUrgency | "all";

const URGENCY_TABS: { id: UrgencyFilter; label: string }[] = [
  { id: "all", label: "Tous" },
  { id: "urgent", label: "Urgents" },
  { id: "normal", label: "Normaux" },
  { id: "newsletter", label: "Newsletters" },
  { id: "spam", label: "Spam" },
];

export default function EmailsPage() {
  const [threads, setThreads] = useState<EmailThreadListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<UrgencyFilter>("all");

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const filters = tab === "all" ? undefined : { urgency: tab };
    emailsApi
      .list(token, filters)
      .then(setThreads)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [tab]);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-bold">Brouillons d'emails</h1>
      <p className="mt-2 text-slate-400">
        Les brouillons générés par Secretary — relis, édite et pousse-les dans ta
        boîte Outlook.
      </p>

      <nav className="mt-6 flex flex-wrap gap-2 text-sm">
        {URGENCY_TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-full border px-3 py-1 ${
              tab === t.id
                ? "border-sky-600 bg-sky-900/30 text-sky-200"
                : "border-slate-800 text-slate-400 hover:border-slate-600 hover:text-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {error && <p className="mt-4 text-red-400">{error}</p>}
      {!threads && !error && <p className="mt-6 text-slate-500">Chargement…</p>}

      {threads && threads.length === 0 && (
        <p className="mt-6 text-slate-500">Aucun email dans cette catégorie.</p>
      )}

      {threads && threads.length > 0 && (
        <ul className="mt-6 divide-y divide-slate-800 overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
          {threads.map((t) => (
            <li key={t.id}>
              <Link
                href={`/app/emails/${t.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-slate-800/50"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <UrgencyBadge urgency={t.urgency} />
                    <span className="truncate font-semibold">{t.subject}</span>
                    <StatusTag status={t.status} />
                  </div>
                  <div className="truncate text-sm text-slate-400">
                    {t.from_address}
                  </div>
                  <div className="mt-1 line-clamp-1 text-xs text-slate-500">
                    {t.snippet}
                  </div>
                </div>
                <div className="shrink-0 text-xs text-slate-500">
                  {t.received_at &&
                    new Date(t.received_at).toLocaleDateString("fr-FR")}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function UrgencyBadge({ urgency }: { urgency: EmailUrgency }) {
  if (urgency === "urgent") {
    return (
      <span className="rounded bg-red-900/50 px-1.5 py-0.5 text-xs font-bold text-red-200">
        URGENT
      </span>
    );
  }
  if (urgency === "newsletter") {
    return (
      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-500">
        newsletter
      </span>
    );
  }
  if (urgency === "spam") {
    return (
      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-500">
        spam
      </span>
    );
  }
  return null;
}

function StatusTag({ status }: { status: string }) {
  const cls =
    status === "drafted"
      ? "bg-sky-900/40 text-sky-300"
      : status === "sent"
        ? "bg-emerald-900/40 text-emerald-400"
        : status === "ignored"
          ? "bg-slate-800 text-slate-500"
          : "bg-amber-900/40 text-amber-300";
  return <span className={`rounded px-1.5 py-0.5 text-xs ${cls}`}>{status}</span>;
}
