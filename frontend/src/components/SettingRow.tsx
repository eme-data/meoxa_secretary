"use client";

import { useState } from "react";
import type { Setting } from "@/lib/api";

interface Props {
  setting: Setting;
  onSave: (value: string) => Promise<void>;
}

export function SettingRow({ setting, onSave }: Props) {
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await onSave(value);
      setSavedAt(Date.now());
      if (setting.is_secret) setValue("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h3 className="font-semibold">{setting.label}</h3>
          {setting.description && (
            <p className="mt-1 text-sm text-slate-400">{setting.description}</p>
          )}
          <p className="mt-1 font-mono text-xs text-slate-500">{setting.key}</p>
        </div>
        <div className="shrink-0 text-right text-xs text-slate-400">
          {setting.is_secret ? (
            setting.has_value ? (
              <span className="rounded bg-emerald-900/40 px-2 py-1 text-emerald-400">
                Configuré — {setting.masked || "••••"}
              </span>
            ) : (
              <span className="rounded bg-amber-900/40 px-2 py-1 text-amber-400">Non défini</span>
            )
          ) : (
            <span className="font-mono text-slate-300">{setting.value || "—"}</span>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        {setting.kind === "select" ? (
          <select
            value={value || setting.value}
            onChange={(e) => setValue(e.target.value)}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            {setting.options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        ) : setting.kind === "bool" ? (
          <select
            value={value || setting.value || "true"}
            onChange={(e) => setValue(e.target.value)}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="true">Activé</option>
            <option value="false">Désactivé</option>
          </select>
        ) : setting.kind === "text" ? (
          <textarea
            rows={3}
            value={value || (setting.is_secret ? "" : setting.value)}
            placeholder={setting.is_secret ? "Saisir pour modifier" : ""}
            onChange={(e) => setValue(e.target.value)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
          />
        ) : (
          <input
            type={setting.is_secret ? "password" : "text"}
            value={value || (setting.is_secret ? "" : setting.value)}
            placeholder={setting.is_secret ? "Saisir pour modifier" : ""}
            onChange={(e) => setValue(e.target.value)}
            autoComplete={setting.is_secret ? "new-password" : "off"}
            autoCorrect="off"
            spellCheck={false}
            data-form-type="other"
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
          />
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !value}
          className="rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
        >
          {saving ? "..." : "Enregistrer"}
        </button>
      </div>

      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      {savedAt && (
        <p className="mt-2 text-sm text-emerald-400">Enregistré.</p>
      )}
    </div>
  );
}
