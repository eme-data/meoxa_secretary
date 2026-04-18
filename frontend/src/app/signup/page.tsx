"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { authApi } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    organization_name: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const tokens = await authApi.signup(form);
      document.cookie = `access_token=${tokens.access_token}; path=/; SameSite=Lax`;
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8">
        <h1 className="text-2xl font-bold">Créer un compte</h1>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <input
            required
            placeholder="Nom de l'organisation"
            value={form.organization_name}
            onChange={(e) => update("organization_name", e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2"
          />
          <input
            required
            placeholder="Nom complet"
            value={form.full_name}
            onChange={(e) => update("full_name", e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2"
          />
          <input
            type="email"
            required
            placeholder="Email"
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2"
          />
          <input
            type="password"
            required
            minLength={10}
            placeholder="Mot de passe (10 caractères min.)"
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2"
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-brand py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {loading ? "..." : "Créer"}
          </button>
        </form>
      </div>
    </main>
  );
}
