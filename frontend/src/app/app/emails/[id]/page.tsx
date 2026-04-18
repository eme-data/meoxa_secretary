"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { emailsApi, type EmailThreadDetail, getToken } from "@/lib/api";

export default function EmailDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [thread, setThread] = useState<EmailThreadDetail | null>(null);
  const [suggestion, setSuggestion] = useState("");
  const [saving, setSaving] = useState(false);
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token || !id) return;
    try {
      const t = await emailsApi.get(token, id);
      setThread(t);
      setSuggestion(t.suggested_reply ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function saveSuggestion() {
    const token = getToken();
    if (!token || !id) return;
    setSaving(true);
    setInfo(null);
    setError(null);
    try {
      const updated = await emailsApi.updateSuggestion(token, id, suggestion);
      setThread(updated);
      setInfo("Suggestion enregistrée.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  async function regenerate() {
    const token = getToken();
    if (!token || !id) return;
    setInfo("Régénération en cours — actualise dans ~30s.");
    await emailsApi.regenerate(token, id);
  }

  async function pushToOutlook() {
    const token = getToken();
    if (!token || !id) return;
    try {
      await saveSuggestion();
      const updated = await emailsApi.pushToOutlook(token, id);
      setThread(updated);
      setInfo("Brouillon créé dans Outlook. Termine et envoie depuis Outlook.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function ignore() {
    const token = getToken();
    if (!token || !id) return;
    if (!confirm("Ignorer ce brouillon ?")) return;
    await emailsApi.ignore(token, id);
    router.push("/app/emails");
  }

  if (error && !thread) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }
  if (!thread) {
    return <main className="mx-auto max-w-3xl px-6 py-10 text-slate-500">Chargement…</main>;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <button
        onClick={() => router.push("/app/emails")}
        className="mb-4 text-sm text-slate-400 hover:text-slate-200"
      >
        ← Retour
      </button>

      <h1 className="text-2xl font-bold">{thread.subject}</h1>
      <p className="mt-1 text-sm text-slate-400">
        De : <span className="font-mono">{thread.from_address}</span>
        {thread.received_at &&
          ` • ${new Date(thread.received_at).toLocaleString("fr-FR")}`}
      </p>

      <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="text-sm font-semibold text-slate-400">Email reçu</h2>
        <pre className="mt-2 max-h-60 overflow-auto whitespace-pre-wrap font-sans text-sm text-slate-200">
          {thread.body_text || thread.snippet}
        </pre>
      </section>

      <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="text-sm font-semibold text-slate-400">
          Brouillon suggéré (éditable)
        </h2>
        <textarea
          rows={12}
          value={suggestion}
          onChange={(e) => setSuggestion(e.target.value)}
          className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
        />
        {info && <p className="mt-2 text-sm text-emerald-400">{info}</p>}
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={saveSuggestion}
            disabled={saving}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
          >
            {saving ? "..." : "Enregistrer"}
          </button>
          <button
            onClick={regenerate}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
          >
            Régénérer avec Claude
          </button>
          <button
            onClick={pushToOutlook}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-dark"
          >
            Créer le brouillon dans Outlook
          </button>
          <button
            onClick={ignore}
            className="rounded-lg border border-red-800 px-4 py-2 text-sm text-red-300 hover:bg-red-900/30"
          >
            Ignorer
          </button>
        </div>
        {thread.outlook_draft_id && (
          <p className="mt-3 text-xs text-slate-500">
            Un brouillon a déjà été créé dans Outlook (ID {thread.outlook_draft_id.slice(0, 12)}…)
            — ce bouton l'écrasera par la version éditée.
          </p>
        )}
      </section>
    </main>
  );
}
