"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  adminApi,
  getToken,
  integrationsApi,
  type OnboardingStatus,
  tenantApi,
} from "@/lib/api";

type StepId =
  | "welcome"
  | "microsoft"
  | "import"
  | "teams"
  | "tone"
  | "signature"
  | "security"
  | "billing"
  | "done";

const STEPS: { id: StepId; label: string }[] = [
  { id: "welcome", label: "Bienvenue" },
  { id: "microsoft", label: "Microsoft 365" },
  { id: "import", label: "Import historique" },
  { id: "teams", label: "Configuration Teams" },
  { id: "tone", label: "Ton des emails" },
  { id: "signature", label: "Signature" },
  { id: "security", label: "Sécurité" },
  { id: "billing", label: "Abonnement" },
  { id: "done", label: "Terminé" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<StepId>("welcome");
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tone, setTone] = useState("professionnel");
  const [signature, setSignature] = useState("");
  const [teamsConfirmed, setTeamsConfirmed] = useState(false);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    try {
      const s = await tenantApi.onboardingStatus(token);
      setStatus(s);
      if (s.completed) router.replace("/app");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }, [router]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Re-synchroniser le statut si l'utilisateur revient depuis l'OAuth Microsoft.
  useEffect(() => {
    const onFocus = () => refresh();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refresh]);

  const currentIdx = STEPS.findIndex((s) => s.id === step);

  async function connectMicrosoft() {
    const token = getToken();
    if (!token) return;
    const { authorize_url } = await integrationsApi.microsoftAuthorize(token);
    window.location.href = authorize_url;
  }

  async function saveTone() {
    const token = getToken();
    if (!token) return;
    await adminApi.updateTenant(token, "emails.reply_tone", tone);
    await refresh();
    setStep("signature");
  }

  async function saveSignature() {
    const token = getToken();
    if (!token) return;
    await adminApi.updateTenant(token, "general.email_signature", signature);
    await refresh();
    setStep("security");
  }

  async function confirmTeams() {
    const token = getToken();
    if (!token) return;
    await tenantApi.confirmTeamsRecording(token);
    setTeamsConfirmed(true);
    await refresh();
    setStep("tone");
  }

  async function launchImport() {
    const token = getToken();
    if (!token) return;
    try {
      await tenantApi.importHistory(token);
      setStep("teams");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function complete() {
    const token = getToken();
    if (!token) return;
    await tenantApi.completeOnboarding(token);
    router.push("/app");
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-3xl font-bold">Mise en route — Pack Secrétariat</h1>
      <p className="mt-2 text-slate-400">
        Cette configuration initiale dure environ 5 minutes.
      </p>

      {/* Stepper */}
      <ol className="mt-8 flex flex-wrap gap-2 text-xs">
        {STEPS.map((s, i) => (
          <li
            key={s.id}
            className={`rounded-full border px-3 py-1 ${
              i < currentIdx
                ? "border-emerald-700 bg-emerald-900/30 text-emerald-300"
                : i === currentIdx
                  ? "border-brand bg-sky-900/30 text-sky-200"
                  : "border-slate-800 text-slate-500"
            }`}
          >
            {i + 1}. {s.label}
          </li>
        ))}
      </ol>

      {error && <p className="mt-4 text-red-400">{error}</p>}

      <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        {step === "welcome" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Bienvenue</h2>
            <p className="text-slate-300">
              On va connecter ton Microsoft 365, configurer ta façon d'écrire, et
              activer l'automatisation. Tu peux interrompre et reprendre à tout moment.
            </p>
            <button
              onClick={() => setStep("microsoft")}
              className="rounded-lg bg-brand px-5 py-2.5 font-semibold text-white hover:bg-brand-dark"
            >
              Commencer
            </button>
          </div>
        )}

        {step === "microsoft" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Connexion Microsoft 365</h2>
            <p className="text-slate-300">
              Autorise l'accès à Outlook (mails), Calendar (agenda) et OneDrive
              (enregistrements Teams). Tu gardes le contrôle — tu peux révoquer à tout moment.
            </p>
            {status?.steps.microsoft_connected ? (
              <div className="flex items-center gap-3">
                <span className="rounded bg-emerald-900/40 px-2 py-1 text-sm text-emerald-400">
                  Connecté
                </span>
                <button
                  onClick={() => setStep("import")}
                  className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark"
                >
                  Continuer
                </button>
              </div>
            ) : (
              <button
                onClick={connectMicrosoft}
                className="rounded-lg bg-brand px-5 py-2.5 font-semibold text-white hover:bg-brand-dark"
              >
                Se connecter à Microsoft
              </button>
            )}
          </div>
        )}

        {step === "import" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Alimenter la mémoire de meoxa</h2>
            <p className="text-slate-300">
              meoxa peut analyser tes <strong>30 derniers jours d'emails</strong> pour
              apprendre ton ton et ton vocabulaire. Les brouillons générés seront
              immédiatement pertinents, sans période de rodage.
            </p>
            <p className="text-xs text-slate-400">
              ⚠️ Aucun email n'est envoyé — on extrait juste les formulations pour la
              mémoire contextuelle. Étape facultative.
            </p>
            <div className="flex gap-2">
              <button
                onClick={launchImport}
                className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark"
              >
                Lancer l'import (≈ 2 min)
              </button>
              <button
                onClick={() => setStep("teams")}
                className="rounded-lg border border-slate-700 px-5 py-2 font-semibold text-slate-200 hover:bg-slate-800"
              >
                Passer
              </button>
            </div>
          </div>
        )}

        {step === "teams" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Activer Teams pour les comptes-rendus</h2>
            <p className="text-slate-300">
              Pour que meoxa génère automatiquement les CR de tes réunions Teams, il faut
              activer deux options dans l'admin Teams. Aucun bot n'est installé — on lit
              simplement les enregistrements déposés dans OneDrive.
            </p>
            <ol className="list-decimal space-y-2 pl-6 text-slate-300">
              <li>
                Va sur{" "}
                <a
                  href="https://admin.teams.microsoft.com/policies/meetings"
                  target="_blank"
                  rel="noreferrer"
                  className="text-sky-400 underline"
                >
                  admin.teams.microsoft.com/policies/meetings
                </a>
              </li>
              <li>
                Dans la policy active, active : <em>Enregistrement automatique des
                réunions</em> et <em>Transcription / sous-titres en direct</em>.
              </li>
              <li>Enregistre. Les prochaines réunions seront captées.</li>
            </ol>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={teamsConfirmed || status?.steps.teams_recording_confirmed || false}
                onChange={(e) => setTeamsConfirmed(e.target.checked)}
              />
              <span>J'ai activé l'enregistrement auto et les sous-titres live</span>
            </label>
            <button
              onClick={confirmTeams}
              disabled={!(teamsConfirmed || status?.steps.teams_recording_confirmed)}
              className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
            >
              Continuer
            </button>
          </div>
        )}

        {step === "tone" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Ton des réponses aux emails</h2>
            <p className="text-slate-300">
              meoxa génère des brouillons de réponse dans ce style.
            </p>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2"
            >
              <option value="professionnel">Professionnel</option>
              <option value="amical">Amical</option>
              <option value="concis">Concis</option>
            </select>
            <button
              onClick={saveTone}
              className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark"
            >
              Continuer
            </button>
          </div>
        )}

        {step === "signature" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Signature email</h2>
            <p className="text-slate-300">
              Ajoutée en fin des brouillons générés. Facultative.
            </p>
            <textarea
              rows={5}
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              placeholder={"Cordialement,\nPrénom Nom\nMDO Services — 06 XX XX XX XX"}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 font-mono text-sm"
            />
            <div className="flex gap-2">
              <button
                onClick={saveSignature}
                className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark"
              >
                Enregistrer
              </button>
              <button
                onClick={() => setStep("security")}
                className="rounded-lg border border-slate-700 px-5 py-2 font-semibold text-slate-200 hover:bg-slate-800"
              >
                Passer
              </button>
            </div>
          </div>
        )}

        {step === "security" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Sécurité (recommandé)</h2>
            <p className="text-slate-300">
              Active la 2FA pour protéger ton compte — meoxa a accès à ta boîte mail,
              un mot de passe seul n'est pas suffisant.
            </p>
            {status?.steps.mfa_enabled ? (
              <div className="flex items-center gap-3">
                <span className="rounded bg-emerald-900/40 px-2 py-1 text-sm text-emerald-400">
                  2FA activée
                </span>
                <button
                  onClick={() => setStep("billing")}
                  className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark"
                >
                  Continuer
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Link
                  href="/app/security"
                  className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark"
                >
                  Activer la 2FA
                </Link>
                <button
                  onClick={() => setStep("billing")}
                  className="rounded-lg border border-slate-700 px-5 py-2 font-semibold text-slate-200 hover:bg-slate-800"
                >
                  Plus tard
                </button>
              </div>
            )}
          </div>
        )}

        {step === "billing" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Abonnement</h2>
            <p className="text-slate-300">
              Pack Secrétariat à 1 490 € HT. Tu peux démarrer l'abonnement maintenant
              ou plus tard depuis l'onglet Facturation.
            </p>
            <div className="flex gap-2">
              {!status?.steps.billing_active && (
                <Link
                  href="/app/billing"
                  className="rounded-lg bg-brand px-5 py-2 font-semibold text-white hover:bg-brand-dark"
                >
                  S'abonner
                </Link>
              )}
              <button
                onClick={() => setStep("done")}
                className="rounded-lg border border-slate-700 px-5 py-2 font-semibold text-slate-200 hover:bg-slate-800"
              >
                {status?.steps.billing_active ? "Continuer" : "Plus tard"}
              </button>
            </div>
          </div>
        )}

        {step === "done" && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Tout est prêt 🎉</h2>
            <p className="text-slate-300">
              Les prochaines réunions Teams seront automatiquement résumées et envoyées
              par mail. Les nouveaux emails auront un brouillon généré dans le style choisi.
            </p>
            <button
              onClick={complete}
              className="rounded-lg bg-brand px-5 py-2.5 font-semibold text-white hover:bg-brand-dark"
            >
              Accéder au tableau de bord
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
