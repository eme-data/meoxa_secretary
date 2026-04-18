"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getToken, searchApi } from "@/lib/api";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Awaited<ReturnType<typeof searchApi.query>> | null>(null);
  const [loading, setLoading] = useState(false);

  const runSearch = useCallback(async (query: string) => {
    if (query.trim().length < 2) {
      setResults(null);
      return;
    }
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const r = await searchApi.query(token, query.trim());
      setResults(r);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => runSearch(q), 300);
    return () => clearTimeout(t);
  }, [q, runSearch]);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-bold">Recherche</h1>
      <p className="mt-2 text-slate-400">
        Cherche dans tes emails et comptes-rendus. Les opérateurs AND / OR / NOT et
        les guillemets sont acceptés.
      </p>

      <input
        autoFocus
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Ex : facture décembre, OR urgent, NOT newsletter…"
        className="mt-6 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-lg"
      />

      {loading && <p className="mt-6 text-slate-500">Recherche…</p>}

      {results && (
        <>
          {results.emails.length === 0 && results.meetings.length === 0 && (
            <p className="mt-8 text-slate-500">Aucun résultat pour « {results.query} ».</p>
          )}

          {results.emails.length > 0 && (
            <section className="mt-8">
              <h2 className="text-lg font-semibold text-slate-300">
                Emails ({results.emails.length})
              </h2>
              <ul className="mt-3 divide-y divide-slate-800 overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
                {results.emails.map((e) => (
                  <li key={e.id}>
                    <Link
                      href={`/app/emails/${e.id}`}
                      className="block px-5 py-4 hover:bg-slate-800/50"
                    >
                      <div className="truncate font-semibold">{e.subject}</div>
                      <div className="truncate text-sm text-slate-400">{e.from_address}</div>
                      <div className="mt-1 line-clamp-2 text-xs text-slate-500">{e.snippet}</div>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {results.meetings.length > 0 && (
            <section className="mt-8">
              <h2 className="text-lg font-semibold text-slate-300">
                Réunions ({results.meetings.length})
              </h2>
              <ul className="mt-3 divide-y divide-slate-800 overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
                {results.meetings.map((m) => (
                  <li key={m.id}>
                    <Link
                      href={`/app/meetings/${m.id}`}
                      className="block px-5 py-4 hover:bg-slate-800/50"
                    >
                      <div className="truncate font-semibold">{m.title}</div>
                      <div className="mt-1 line-clamp-3 text-xs text-slate-500">{m.excerpt}</div>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
