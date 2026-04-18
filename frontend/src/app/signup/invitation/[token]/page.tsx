"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { invitationsApi } from "@/lib/api";

export default function AcceptInvitationPage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const [preview, setPreview] = useState<{
    email: string;
    organization_name: string;
    role: string;
  } | null>(null);
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    invitationsApi
      .preview(token)
      .then(setPreview)
      .catch((e) => setError(e instanceof Error ? e.message : "Lien invalide"));
  }, [token]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const tokens = await invitationsApi.accept({
        token,
        password,
        full_name: fullName,
      });
      document.cookie = `access_token=${tokens.access_token}; path=/; SameSite=Lax`;
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  if (error && !preview) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8">
          <h1 className="text-2xl font-bold">Lien invalide</h1>
          <p className="mt-3 text-slate-300">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8">
        <h1 className="text-2xl font-bold">Rejoindre {preview?.organization_name ?? "…"}</h1>
        {preview && (
          <p className="mt-2 text-sm text-slate-400">
            Tu es invité(e) en tant que <strong>{preview.role}</strong> —{" "}
            <span className="font-mono">{preview.email}</span>
          </p>
        )}
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <input
            required
            placeholder="Nom complet"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2"
          />
          <input
            required
            type="password"
            minLength={10}
            placeholder="Mot de passe (≥ 10 car.)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2"
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading || !fullName || password.length < 10}
            className="w-full rounded-lg bg-brand py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {loading ? "..." : "Créer le compte"}
          </button>
        </form>
      </div>
    </main>
  );
}
