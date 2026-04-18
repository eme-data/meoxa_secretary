"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, type MeetingDetail, meetingsApi } from "@/lib/api";

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token || !id) return;
    meetingsApi
      .detail(token, id)
      .then(setMeeting)
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
  }, [id]);

  async function resend() {
    const token = getToken();
    if (!token || !id) return;
    try {
      const r = await meetingsApi.resendEmail(token, id);
      setInfo(`CR renvoyé à ${r.to}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  if (error && !meeting) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }
  if (!meeting) {
    return <main className="mx-auto max-w-3xl px-6 py-10 text-slate-500">Chargement…</main>;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <button
        onClick={() => router.push("/app/meetings")}
        className="mb-4 text-sm text-slate-400 hover:text-slate-200"
      >
        ← Retour
      </button>

      <h1 className="text-2xl font-bold">{meeting.title}</h1>
      <p className="mt-1 text-sm text-slate-400">
        {new Date(meeting.starts_at).toLocaleString("fr-FR")}
        {meeting.ends_at && ` → ${new Date(meeting.ends_at).toLocaleTimeString("fr-FR")}`}
        {" • "}
        <span className="font-mono">{meeting.organizer_email}</span>
      </p>

      {info && <p className="mt-3 text-sm text-emerald-400">{info}</p>}
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      {meeting.summary_markdown ? (
        <>
          <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-lg font-semibold">Compte-rendu</h2>
            <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200">
              {meeting.summary_markdown}
            </pre>
            <div className="mt-4 flex gap-2">
              <button
                onClick={resend}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
              >
                Renvoyer le CR par mail
              </button>
            </div>
          </section>

          {meeting.action_items && meeting.action_items.length > 0 && (
            <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
              <h2 className="text-lg font-semibold">Actions extraites</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {meeting.action_items.map((a, i) => (
                  <li
                    key={i}
                    className="rounded border border-slate-800 bg-slate-950 px-3 py-2"
                  >
                    <div className="font-semibold">{a.title}</div>
                    <div className="text-xs text-slate-400">
                      {a.owner_email && `→ ${a.owner_email}`}
                      {a.due_date && ` • échéance ${a.due_date}`}
                    </div>
                  </li>
                ))}
              </ul>
              {meeting.planner_task_ids && meeting.planner_task_ids.length > 0 && (
                <p className="mt-3 text-xs text-emerald-400">
                  ✓ {meeting.planner_task_ids.length} tâche(s) créée(s) dans Microsoft Planner
                </p>
              )}
            </section>
          )}
        </>
      ) : (
        <section className="mt-6 rounded-xl border border-amber-800 bg-amber-900/20 p-6">
          <p className="text-amber-300">
            CR non encore disponible — statut : <strong>{meeting.status}</strong>.
          </p>
          <p className="mt-2 text-sm text-slate-400">
            Transcription : {meeting.raw_text_length} caractères capturés.
          </p>
        </section>
      )}
    </main>
  );
}
