"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi, authApi, getToken, type Setting } from "@/lib/api";
import { SettingRow } from "@/components/SettingRow";

export default function PlatformAdminPage() {
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
        const me = await authApi.me(token);
        if (!me.is_superadmin) {
          setError("Accès réservé au super-admin de la plateforme.");
          return;
        }
        setSettings(await adminApi.listPlatform(token));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erreur de chargement");
      }
    })();
  }, [router]);

  async function save(key: string, value: string) {
    const token = getToken();
    if (!token) return;
    const updated = await adminApi.updatePlatform(token, key, value);
    setSettings((prev) => prev?.map((s) => (s.key === key ? updated : s)) ?? null);
  }

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }

  const groups = groupByPrefix(settings ?? []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-3xl font-bold">Configuration plateforme</h1>
      <p className="mt-2 text-slate-400">
        Clés communes à tous les tenants — uniquement accessibles au super-admin MDO.
      </p>

      {!settings && <p className="mt-6 text-slate-500">Chargement…</p>}

      {settings &&
        Object.entries(groups).map(([group, items]) => (
          <section key={group} className="mt-10">
            <h2 className="mb-3 text-xl font-semibold capitalize">{groupLabel(group)}</h2>
            <div className="space-y-3">
              {items.map((s) => (
                <SettingRow key={s.key} setting={s} onSave={(v) => save(s.key, v)} />
              ))}
            </div>
          </section>
        ))}
    </main>
  );
}

function groupByPrefix(items: Setting[]): Record<string, Setting[]> {
  const out: Record<string, Setting[]> = {};
  for (const s of items) {
    const group = s.key.split(".")[0];
    (out[group] ??= []).push(s);
  }
  return out;
}

function groupLabel(group: string): string {
  const labels: Record<string, string> = {
    anthropic: "Anthropic (Claude)",
    microsoft: "Microsoft 365",
    teams_bot: "Bot Teams",
    storage: "Stockage S3",
  };
  return labels[group] ?? group;
}
