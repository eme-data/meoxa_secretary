"use client";

import { useEffect, useState } from "react";
import { type EmailTemplate, getToken, templatesApi } from "@/lib/api";

const SUGGESTED_PROMPTS = [
  {
    name: "Accusé de réception",
    description: "Réponse rapide pour confirmer bonne réception",
    prompt:
      "Rédige un accusé de réception court et poli en français. Confirme la bonne réception du message et indique un délai de traitement raisonnable (2-3 jours ouvrés). Pas plus de 4 phrases.",
  },
  {
    name: "Demande de devis",
    description: "Réponse à un prospect qui demande un prix",
    prompt:
      "Rédige une réponse à une demande de devis. Remercie pour l'intérêt, pose 2-3 questions pour cadrer le besoin (budget, délai, périmètre), propose un appel de 30 min dans la semaine.",
  },
  {
    name: "Relance de paiement",
    description: "Rappel client facture impayée",
    prompt:
      "Rédige une relance client pour facture impayée. Ton professionnel mais ferme, rappelle le numéro de facture et le montant, demande un règlement sous 7 jours. Propose un moyen de contact pour discuter.",
  },
  {
    name: "Remerciement",
    description: "Après un rendez-vous ou une transaction",
    prompt:
      "Rédige un remerciement court et sincère après un rendez-vous ou une transaction réussie. 3-4 phrases max, ton chaleureux mais professionnel.",
  },
];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<EmailTemplate[] | null>(null);
  const [editing, setEditing] = useState<EmailTemplate | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const token = getToken();
    if (!token) return;
    try {
      setTemplates(await templatesApi.list(token));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function save(form: { name: string; description: string; prompt: string }) {
    const token = getToken();
    if (!token) return;
    if (editing) {
      await templatesApi.update(token, editing.id, form);
    } else {
      await templatesApi.create(token, form);
    }
    setEditing(null);
    await refresh();
  }

  async function remove(id: string) {
    const token = getToken();
    if (!token) return;
    if (!confirm("Supprimer ce template ?")) return;
    await templatesApi.remove(token, id);
    await refresh();
  }

  async function addSuggested(sug: (typeof SUGGESTED_PROMPTS)[number]) {
    const token = getToken();
    if (!token) return;
    await templatesApi.create(token, sug);
    await refresh();
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-3xl font-bold">Templates d'emails</h1>
      <p className="mt-2 text-slate-400">
        Des prompts réutilisables. Depuis le détail d'un email, tu pourras appliquer
        un template pour générer un brouillon dans ce style précis.
      </p>

      {error && <p className="mt-4 text-red-400">{error}</p>}

      {!editing && templates && templates.length === 0 && (
        <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-lg font-semibold">Templates suggérés</h2>
          <p className="mt-1 text-sm text-slate-400">
            Clique pour en ajouter un en un clic, puis tu pourras l'ajuster.
          </p>
          <ul className="mt-4 space-y-2">
            {SUGGESTED_PROMPTS.map((s) => (
              <li
                key={s.name}
                className="flex items-center justify-between gap-3 rounded border border-slate-800 bg-slate-950 px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="font-semibold">{s.name}</div>
                  <div className="truncate text-xs text-slate-500">{s.description}</div>
                </div>
                <button
                  onClick={() => addSuggested(s)}
                  className="shrink-0 rounded-lg bg-brand px-3 py-1 text-xs font-semibold text-white hover:bg-brand-dark"
                >
                  + Ajouter
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!editing && templates && templates.length > 0 && (
        <ul className="mt-8 space-y-3">
          {templates.map((t) => (
            <li
              key={t.id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{t.name}</h3>
                  <p className="text-xs text-slate-500">{t.description}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditing(t)}
                    className="rounded-lg border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800"
                  >
                    Éditer
                  </button>
                  <button
                    onClick={() => remove(t.id)}
                    className="rounded-lg border border-red-800 px-3 py-1 text-xs text-red-300 hover:bg-red-900/30"
                  >
                    Suppr.
                  </button>
                </div>
              </div>
              <p className="mt-3 line-clamp-2 text-sm text-slate-300">{t.prompt}</p>
            </li>
          ))}
        </ul>
      )}

      {!editing && templates && templates.length > 0 && (
        <button
          onClick={() =>
            setEditing({ id: "", name: "", description: "", prompt: "" })
          }
          className="mt-6 rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
        >
          + Nouveau template
        </button>
      )}

      {editing && (
        <TemplateForm
          initial={editing}
          onSubmit={save}
          onCancel={() => setEditing(null)}
        />
      )}
    </main>
  );
}

function TemplateForm({
  initial,
  onSubmit,
  onCancel,
}: {
  initial: EmailTemplate;
  onSubmit: (form: { name: string; description: string; prompt: string }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial.name);
  const [description, setDescription] = useState(initial.description);
  const [prompt, setPrompt] = useState(initial.prompt);

  return (
    <form
      className="mt-8 space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-6"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ name, description, prompt });
      }}
    >
      <h2 className="text-xl font-semibold">
        {initial.id ? "Éditer le template" : "Nouveau template"}
      </h2>
      <input
        required
        placeholder="Nom (ex : Accusé de réception)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
      />
      <input
        placeholder="Description courte (optionnelle)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
      />
      <textarea
        required
        rows={8}
        placeholder="Prompt pour Claude : comment il doit rédiger quand ce template est choisi…"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
      />
      <div className="flex gap-2">
        <button
          type="submit"
          className="rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark"
        >
          Enregistrer
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-700 px-4 py-2 hover:bg-slate-800"
        >
          Annuler
        </button>
      </div>
    </form>
  );
}
