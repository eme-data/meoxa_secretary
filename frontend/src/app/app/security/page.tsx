"use client";

import { useEffect, useState } from "react";
import { authApi, getToken } from "@/lib/api";

export default function SecurityPage() {
  const [totpEnabled, setTotpEnabled] = useState<boolean | null>(null);
  const [qrPng, setQrPng] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    authApi.me(token).then((me) => setTotpEnabled(me.totp_enabled));
  }, []);

  async function startEnroll() {
    const token = getToken();
    if (!token) return;
    setError(null);
    const res = await authApi.mfaEnrollStart(token);
    setQrPng(res.qr_code_png_b64);
    setSecret(res.secret);
  }

  async function confirmEnroll() {
    const token = getToken();
    if (!token || !secret) return;
    try {
      const res = await authApi.mfaEnrollConfirm(token, { secret, code });
      setBackupCodes(res.backup_codes);
      setTotpEnabled(true);
      setQrPng(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function disable() {
    const token = getToken();
    if (!token) return;
    await authApi.mfaDisable(token);
    setTotpEnabled(false);
    setBackupCodes(null);
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-3xl font-bold">Sécurité</h1>

      <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-xl font-semibold">Authentification à deux facteurs (TOTP)</h2>
        <p className="mt-2 text-slate-400">
          Ajoute une couche de sécurité en utilisant une application comme 1Password,
          Authy, ou Google Authenticator.
        </p>

        {totpEnabled === null && <p className="mt-4 text-slate-500">Chargement…</p>}

        {totpEnabled === false && !qrPng && (
          <button
            onClick={startEnroll}
            className="mt-4 rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark"
          >
            Activer la 2FA
          </button>
        )}

        {qrPng && (
          <div className="mt-6 space-y-4">
            <p className="text-sm text-slate-300">
              Scanne ce QR code dans ton application d'authentification :
            </p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:image/png;base64,${qrPng}`}
              alt="QR code MFA"
              className="rounded border border-slate-700"
              width={200}
              height={200}
            />
            <p className="text-xs text-slate-500">
              Ou saisis manuellement : <code className="font-mono">{secret}</code>
            </p>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Code à 6 chiffres"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 font-mono"
            />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
              onClick={confirmEnroll}
              disabled={!code}
              className="rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
            >
              Confirmer
            </button>
          </div>
        )}

        {backupCodes && (
          <div className="mt-6 rounded-lg border border-amber-800 bg-amber-900/30 p-4">
            <p className="font-semibold text-amber-300">
              Conserve ces codes de secours — ils ne s'afficheront plus jamais
            </p>
            <ul className="mt-3 grid grid-cols-2 gap-2 font-mono text-sm">
              {backupCodes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}

        {totpEnabled === true && !backupCodes && (
          <div className="mt-4 flex items-center gap-3">
            <span className="rounded bg-emerald-900/40 px-2 py-1 text-sm text-emerald-400">
              Activée
            </span>
            <button
              onClick={disable}
              className="rounded-lg border border-red-800 px-3 py-1 text-sm text-red-300 hover:bg-red-900/30"
            >
              Désactiver
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
