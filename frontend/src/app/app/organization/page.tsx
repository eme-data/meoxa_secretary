"use client";

import { useEffect, useState } from "react";
import { type BrandingOut, dpaApi, getToken, tenantApi } from "@/lib/api";

export default function OrganizationPage() {
  const [branding, setBranding] = useState<BrandingOut | null>(null);
  const [primary, setPrimary] = useState("");
  const [accent, setAccent] = useState("");
  const [uploading, setUploading] = useState(false);
  const [deletion, setDeletion] = useState<{
    scheduled_at: string | null;
    grace_period_days?: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    tenantApi.getBranding(token).then((b) => {
      setBranding(b);
      setPrimary(b.primary_color ?? "");
      setAccent(b.accent_color ?? "");
    });
    tenantApi.deletionStatus(token).then(setDeletion);
  }, []);

  async function saveColors() {
    const token = getToken();
    if (!token) return;
    const b = await tenantApi.updateBranding(token, {
      primary_color: primary,
      accent_color: accent,
    });
    setBranding(b);
    setInfo("Couleurs enregistrées.");
  }

  async function uploadLogo(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const token = getToken();
    if (!file || !token) return;
    setUploading(true);
    setError(null);
    try {
      const b = await tenantApi.uploadLogo(token, file);
      setBranding(b);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur upload");
    } finally {
      setUploading(false);
    }
  }

  async function exportData() {
    const token = getToken();
    if (!token) return;
    await tenantApi.requestExport(token);
    setInfo("Export demandé — tu recevras un lien quand il sera prêt.");
  }

  async function scheduleDelete() {
    if (!confirm("Programmer la suppression définitive dans 30 jours ?")) return;
    const token = getToken();
    if (!token) return;
    const res = await tenantApi.requestDeletion(token);
    setDeletion({ scheduled_at: res.scheduled_at, grace_period_days: 30 });
  }

  async function cancelDelete() {
    const token = getToken();
    if (!token) return;
    await tenantApi.cancelDeletion(token);
    setDeletion({ scheduled_at: null });
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-3xl font-bold">Organisation</h1>

      {error && <p className="mt-4 text-red-400">{error}</p>}
      {info && <p className="mt-4 text-emerald-400">{info}</p>}

      <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-xl font-semibold">Branding</h2>

        <div className="mt-4 flex items-center gap-4">
          {branding?.logo_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={branding.logo_url}
              alt="Logo"
              className="h-16 w-16 rounded border border-slate-700 object-contain"
            />
          )}
          <label className="rounded-lg border border-slate-700 px-4 py-2 hover:bg-slate-800 cursor-pointer">
            {uploading ? "Upload..." : "Téléverser un logo"}
            <input
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp"
              onChange={uploadLogo}
              className="hidden"
            />
          </label>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm text-slate-400">Couleur primaire</span>
            <input
              value={primary}
              onChange={(e) => setPrimary(e.target.value)}
              placeholder="#0ea5e9"
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm text-slate-400">Couleur d'accent</span>
            <input
              value={accent}
              onChange={(e) => setAccent(e.target.value)}
              placeholder="#0369a1"
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
            />
          </label>
        </div>
        <button
          onClick={saveColors}
          className="mt-4 rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark"
        >
          Enregistrer
        </button>
      </section>

      <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-xl font-semibold">Données (RGPD)</h2>
        <p className="mt-2 text-slate-400">
          Exporter toutes les données de l'organisation ou planifier leur suppression.
        </p>
        <div className="mt-4 flex gap-3">
          <button
            onClick={exportData}
            className="rounded-lg border border-slate-700 px-4 py-2 hover:bg-slate-800"
          >
            Exporter mes données
          </button>
          {!deletion?.scheduled_at && (
            <button
              onClick={scheduleDelete}
              className="rounded-lg border border-red-800 px-4 py-2 text-red-300 hover:bg-red-900/30"
            >
              Supprimer l'organisation
            </button>
          )}
          {deletion?.scheduled_at && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-amber-300">
                Suppression prévue le{" "}
                {new Date(deletion.scheduled_at).toLocaleDateString("fr-FR")}
              </span>
              <button
                onClick={cancelDelete}
                className="rounded-lg border border-slate-700 px-3 py-1 text-sm hover:bg-slate-800"
              >
                Annuler
              </button>
            </div>
          )}
        </div>
      </section>

      <DpaSection />
    </main>
  );
}

function DpaSection() {
  const [form, setForm] = useState({
    legal_name: "",
    address: "",
    signatory_name: "",
    signatory_title: "",
    dpo_email: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function generate() {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const html = await dpaApi.generate(token, {
        legal_name: form.legal_name,
        address: form.address,
        signatory_name: form.signatory_name,
        signatory_title: form.signatory_title,
        dpo_email: form.dpo_email || undefined,
      });
      const blob = new Blob([html], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = form.legal_name && form.address && form.signatory_name && form.signatory_title;

  return (
    <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
      <h2 className="text-xl font-semibold">Contrat de sous-traitance (DPA)</h2>
      <p className="mt-2 text-slate-400">
        Génère un DPA conforme art. 28 RGPD, pré-rempli avec tes informations et la
        liste des sous-traitants (Anthropic, Microsoft, Stripe, Voyage, hébergeur).
      </p>
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <input
          placeholder="Raison sociale du client"
          value={form.legal_name}
          onChange={(e) => update("legal_name", e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        />
        <input
          placeholder="Adresse complète"
          value={form.address}
          onChange={(e) => update("address", e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        />
        <input
          placeholder="Nom du signataire"
          value={form.signatory_name}
          onChange={(e) => update("signatory_name", e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        />
        <input
          placeholder="Fonction du signataire"
          value={form.signatory_title}
          onChange={(e) => update("signatory_title", e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        />
        <input
          type="email"
          placeholder="Email DPO (facultatif)"
          value={form.dpo_email}
          onChange={(e) => update("dpo_email", e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm sm:col-span-2"
        />
      </div>
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      <p className="mt-3 text-xs text-slate-500">
        ⚠️ À faire relire par un avocat pour les contrats à fort enjeu.
      </p>
      <button
        onClick={generate}
        disabled={!canSubmit || loading}
        className="mt-4 rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {loading ? "..." : "Générer le DPA"}
      </button>
    </section>
  );
}
