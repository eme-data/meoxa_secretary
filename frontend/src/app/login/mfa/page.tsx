"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { authApi } from "@/lib/api";

export default function MfaLoginPage() {
  const router = useRouter();
  const [challenge, setChallenge] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = sessionStorage.getItem("mfa_challenge");
    if (!saved) {
      router.replace("/login");
      return;
    }
    setChallenge(saved);
  }, [router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!challenge) return;
    setLoading(true);
    setError(null);
    try {
      const tokens = await authApi.mfaLogin({ challenge_token: challenge, code });
      document.cookie = `access_token=${tokens.access_token}; path=/; SameSite=Lax`;
      sessionStorage.removeItem("mfa_challenge");
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Code invalide");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8">
        <h1 className="text-2xl font-bold">Vérification en 2 étapes</h1>
        <p className="mt-2 text-sm text-slate-400">
          Entre le code à 6 chiffres de ton application d'authentification (ou un code de secours).
        </p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <input
            autoFocus
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Code"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 font-mono tracking-widest"
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading || !code}
            className="w-full rounded-lg bg-brand py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {loading ? "..." : "Valider"}
          </button>
        </form>
      </div>
    </main>
  );
}
