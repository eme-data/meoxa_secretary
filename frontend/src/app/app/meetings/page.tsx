"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getToken, type MeetingListItem, meetingsApi } from "@/lib/api";

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<MeetingListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    meetingsApi
      .list(token)
      .then(setMeetings)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-bold">Réunions & comptes-rendus</h1>
      <p className="mt-2 text-slate-400">
        Historique des réunions Teams traitées par meoxa.
      </p>

      {error && <p className="mt-4 text-red-400">{error}</p>}
      {!meetings && !error && <p className="mt-6 text-slate-500">Chargement…</p>}

      {meetings && meetings.length === 0 && (
        <p className="mt-6 text-slate-500">
          Aucune réunion traitée. Active l'enregistrement auto + sous-titres live dans Teams,
          les CR apparaîtront ici.
        </p>
      )}

      {meetings && meetings.length > 0 && (
        <ul className="mt-6 divide-y divide-slate-800 overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
          {meetings.map((m) => (
            <li key={m.id}>
              <Link
                href={`/app/meetings/${m.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-slate-800/50"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold">{m.title}</div>
                  <div className="text-xs text-slate-400">
                    {new Date(m.starts_at).toLocaleString("fr-FR")}
                  </div>
                </div>
                <StatusTag status={m.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function StatusTag({ status }: { status: string }) {
  const cls =
    status === "ready"
      ? "bg-emerald-900/40 text-emerald-400"
      : status === "failed"
        ? "bg-red-900/40 text-red-400"
        : status.includes("ing")
          ? "bg-amber-900/40 text-amber-300"
          : "bg-slate-800 text-slate-400";
  return <span className={`rounded px-2 py-0.5 text-xs ${cls}`}>{status}</span>;
}
