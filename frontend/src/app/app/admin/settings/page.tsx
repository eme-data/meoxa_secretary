"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi, getToken, type Setting } from "@/lib/api";
import { SettingRow } from "@/components/SettingRow";

export default function TenantSettingsPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<Setting[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        setSettings(await adminApi.listTenant(token));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erreur");
      }
    })();
  }, [router]);

  async function save(key: string, value: string) {
    const token = getToken();
    if (!token) return;
    const updated = await adminApi.updateTenant(token, key, value);
    setSettings((prev) => prev?.map((s) => (s.key === key ? updated : s)) ?? null);
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-3xl font-bold">Paramètres de l'organisation</h1>
      <p className="mt-2 text-slate-400">
        Préférences spécifiques à votre tenant — modifiables par les admins/owners.
      </p>

      {error && <p className="mt-6 text-red-400">{error}</p>}
      {!settings && !error && <p className="mt-6 text-slate-500">Chargement…</p>}

      {settings && (
        <div className="mt-8 space-y-3">
          {settings.map((s) => (
            <SettingRow key={s.key} setting={s} onSave={(v) => save(s.key, v)} />
          ))}
        </div>
      )}
    </main>
  );
}
