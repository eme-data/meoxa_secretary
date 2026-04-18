"use client";

import { useEffect, useState } from "react";
import { getToken, teamApi, type Invitation, type Member } from "@/lib/api";

export default function TeamPage() {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [invitations, setInvitations] = useState<Invitation[] | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const token = getToken();
    if (!token) return;
    try {
      const [m, i] = await Promise.all([
        teamApi.listMembers(token),
        teamApi.listInvitations(token).catch(() => [] as Invitation[]),
      ]);
      setMembers(m);
      setInvitations(i);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function invite() {
    const token = getToken();
    if (!token || !inviteEmail) return;
    try {
      await teamApi.createInvitation(token, { email: inviteEmail, role: inviteRole });
      setInviteEmail("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur invitation");
    }
  }

  async function revoke(id: string) {
    const token = getToken();
    if (!token) return;
    await teamApi.revokeInvitation(token, id);
    await refresh();
  }

  async function changeRole(userId: string, role: string) {
    const token = getToken();
    if (!token) return;
    await teamApi.changeRole(token, userId, role);
    await refresh();
  }

  async function removeMember(userId: string) {
    const token = getToken();
    if (!token) return;
    if (!confirm("Retirer ce membre de l'organisation ?")) return;
    await teamApi.removeMember(token, userId);
    await refresh();
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-3xl font-bold">Équipe</h1>
      {error && <p className="mt-4 text-red-400">{error}</p>}

      <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-xl font-semibold">Inviter un membre</h2>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input
            type="email"
            placeholder="email@exemple.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="member">Membre</option>
            <option value="admin">Admin</option>
            <option value="owner">Owner</option>
          </select>
          <button
            onClick={invite}
            disabled={!inviteEmail}
            className="rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            Inviter
          </button>
        </div>
      </section>

      {invitations && invitations.length > 0 && (
        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-xl font-semibold">Invitations en attente</h2>
          <ul className="mt-4 space-y-3">
            {invitations.map((inv) => (
              <li key={inv.id} className="flex items-center justify-between gap-2">
                <div>
                  <div className="font-semibold">{inv.email}</div>
                  <div className="text-xs text-slate-400">
                    Rôle {inv.role} — expire{" "}
                    {new Date(inv.expires_at).toLocaleDateString("fr-FR")}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigator.clipboard.writeText(inv.accept_url)}
                    className="rounded-lg border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800"
                    title={inv.accept_url}
                  >
                    Copier le lien
                  </button>
                  <button
                    onClick={() => revoke(inv.id)}
                    className="rounded-lg border border-red-800 px-3 py-1 text-xs text-red-300 hover:bg-red-900/30"
                  >
                    Révoquer
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-xl font-semibold">Membres</h2>
        {!members && <p className="mt-4 text-slate-500">Chargement…</p>}
        {members && (
          <ul className="mt-4 space-y-3">
            {members.map((m) => (
              <li
                key={m.user_id}
                className="flex items-center justify-between gap-2 rounded border border-slate-800 bg-slate-950 px-3 py-2"
              >
                <div>
                  <div className="font-semibold">{m.full_name}</div>
                  <div className="text-xs text-slate-400">
                    {m.email} {m.totp_enabled && "· 2FA ✓"}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={m.role}
                    onChange={(e) => changeRole(m.user_id, e.target.value)}
                    className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm"
                  >
                    <option value="member">Membre</option>
                    <option value="admin">Admin</option>
                    <option value="owner">Owner</option>
                  </select>
                  <button
                    onClick={() => removeMember(m.user_id)}
                    className="rounded border border-red-800 px-2 py-1 text-xs text-red-300 hover:bg-red-900/30"
                  >
                    Retirer
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
