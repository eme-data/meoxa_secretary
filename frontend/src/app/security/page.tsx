import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Sécurité & confidentialité",
  description:
    "Détail complet des mesures techniques et organisationnelles de Secretary : chiffrement, isolation multi-tenant, RGPD, 2FA, audit, sauvegardes.",
};

export default function SecurityPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-xl font-bold tracking-tight">
            Secretary<span className="text-brand">.</span>
            <span className="ml-2 text-xs font-normal text-slate-500">by Meoxa</span>
          </Link>
          <div className="flex gap-4 text-sm">
            <Link href="/login" className="text-slate-300 hover:text-white">
              Se connecter
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark"
            >
              Démarrer
            </Link>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-4 inline-block rounded-full border border-emerald-700/40 bg-emerald-900/20 px-3 py-1 text-xs font-semibold text-emerald-300">
          Document de transparence technique
        </div>
        <h1 className="text-4xl font-bold md:text-5xl">Sécurité & confidentialité</h1>
        <p className="mt-4 text-lg text-slate-300">
          Secretary manipule des données sensibles : emails professionnels,
          enregistrements de réunions, données d'agenda. Cette page détaille
          précisément les mesures techniques et organisationnelles en place.
        </p>
        <p className="mt-2 text-sm text-slate-500">
          Version en vigueur au {new Date().toLocaleDateString("fr-FR")} ·
          Document ouvert pour l'évaluation RSSI / DSI.
        </p>

        <Section title="Architecture et hébergement">
          <Item
            title="Hébergement souverain en Union européenne"
            text="Infrastructure dédiée en France, opérée directement par Meoxa. Aucun sous-traitant d'hébergement aux États-Unis. Les serveurs applicatifs, les bases de données et les sauvegardes sont tous localisés dans l'UE."
          />
          <Item
            title="Multi-tenant avec isolation stricte au niveau SQL"
            text="PostgreSQL Row-Level Security est activé sur toutes les tables contenant des données métier (emails, réunions, intégrations, settings). Chaque requête applicative est scopée par `app.tenant_id` — il est techniquement impossible qu'un tenant accède aux données d'un autre, même en cas de bug applicatif ou d'injection SQL réussie."
          />
          <Item
            title="Chiffrement en transit"
            text="TLS 1.2 minimum (TLS 1.3 par défaut) sur toutes les communications externes. Certificats Let's Encrypt renouvelés automatiquement. HSTS activé avec preload. Aucun fallback HTTP."
          />
          <Item
            title="Chiffrement au repos"
            text="Les secrets applicatifs (clés API tierces, tokens OAuth Microsoft, clés Stripe, secrets TOTP, codes de secours MFA) sont chiffrés via Fernet (AES-128-CBC + HMAC-SHA256) avant persistance. La clé maîtresse est stockée en variable d'environnement et n'apparaît jamais en base. Les sauvegardes sont chiffrées avant transfert off-site."
          />
        </Section>

        <Section title="Authentification et accès">
          <Item
            title="Authentification à 2 facteurs (MFA TOTP)"
            text="Second facteur TOTP conforme à la RFC 6238 disponible pour tous les utilisateurs, obligatoire pour les super-administrateurs de la plateforme. 10 codes de secours générés à l'enrôlement, utilisables une seule fois, stockés chiffrés."
          />
          <Item
            title="Sessions courtes avec refresh rotatif"
            text="Access token JWT de 30 minutes, refresh token de 14 jours. Algorithme HS256 avec secret de 256 bits. Aucun refresh token n'est stocké en base — seul le JWT signé fait foi."
          />
          <Item
            title="Rate limiting anti-bruteforce"
            text="Routes d'authentification protégées par slowapi avec storage Redis partagé entre workers : 10 tentatives/minute sur /auth/login, 5/heure sur /auth/signup."
          />
          <Item
            title="Rôles granulaires par tenant"
            text="Hiérarchie OWNER > ADMIN > MEMBER avec contrôle fin des actions (invitations, modification des paramètres, accès à la facturation). Contrainte au niveau base : il doit toujours rester au moins un OWNER par tenant actif."
          />
        </Section>

        <Section title="Traitement des données">
          <Item
            title="Secretary est un logiciel — aucun humain ne lit vos données"
            text="Tout le traitement (lecture d'emails, génération de brouillons, transcription de réunions, création de CR) est automatisé. Les collaborateurs de Meoxa n'ont accès aux données des clients que dans des cas exceptionnels d'intervention support explicitement autorisés."
          />
          <Item
            title="Pas d'entraînement IA sur vos données"
            text="Les données transmises à Anthropic (modèle Claude) ne sont pas utilisées pour entraîner de modèles, conformément au DPA Anthropic Enterprise. Les données Voyage AI (embeddings) non plus. Vos données restent vos données."
          />
          <Item
            title="Mémoire contextuelle privée par tenant"
            text="L'indexation RAG (Voyage AI + pgvector) produit des embeddings stockés dans votre tenant uniquement. Aucun embedding n'est partagé entre tenants. Lorsque vous exercez votre droit à l'oubli, les embeddings sont supprimés en cascade."
          />
        </Section>

        <Section title="Journalisation et auditabilité">
          <Item
            title="Journal d'audit immuable"
            text="Toutes les actions sensibles sont tracées dans une table `audit_logs` append-only : login/logout, changement de mot de passe, activation/désactivation de la MFA, modifications des paramètres plateforme et tenant, invitations, changements de rôles, export RGPD, demandes de suppression."
          />
          <Item
            title="Monitoring d'erreurs self-hosted (GlitchTip)"
            text="Capture des erreurs applicatives avec scrubbing automatique des données sensibles avant envoi (headers d'auth, cookies, champs password/token). Déployé sur la même infrastructure, jamais envoyé à des tiers."
          />
          <Item
            title="Suivi de consommation LLM"
            text="Chaque appel aux modèles Claude est tracé dans `llm_usage_events` (tokens entrée/sortie, coût estimé, tâche, modèle) — transparence complète sur la consommation du tenant."
          />
        </Section>

        <Section title="Conformité RGPD">
          <Item
            title="Export en un clic"
            text="Export ZIP complet des données du tenant (users, memberships, emails, meetings, transcripts, intégrations sans tokens, paramètres, audit log) accessible depuis /app/organization."
          />
          <Item
            title="Droit à l'oubli avec délai de grâce"
            text="Sur demande, suppression différée 30 jours (permet la réversibilité), puis purge hard avec révocation des souscriptions Graph côté Microsoft."
          />
          <Item
            title="Rétention configurable"
            text="Chaque tenant choisit combien de jours Secretary conserve ses transcriptions de réunions et leurs embeddings (de 1 à 3 650 jours, ou 0 = rétention illimitée). Purge automatique quotidienne par Celery beat."
          />
          <Item
            title="DPA (contrat de sous-traitance) téléchargeable"
            text="Template conforme à l'article 28 RGPD, pré-rempli avec les sous-traitants ultérieurs (Anthropic, Microsoft, Voyage, Stripe, hébergeur), générable depuis l'interface. À faire signer lors de la souscription."
          />
        </Section>

        <Section title="Sauvegardes et continuité">
          <Item
            title="Backup PostgreSQL quotidien"
            text="Dump chiffré quotidien à 03h00 UTC, rétention locale 14 jours, copie off-site via rclone vers Backblaze B2 ou S3-compatible."
          />
          <Item
            title="Plan de reprise d'activité"
            text="Les sauvegardes sont testées régulièrement en restauration sur un environnement isolé. Objectif RPO (perte de données acceptable) : 24 heures. Objectif RTO (reprise) : 4 heures."
          />
          <Item
            title="Disponibilité cible"
            text="99 % sur 12 mois glissants. Statut public en temps réel sur notre page Status."
          />
        </Section>

        <Section title="Sous-traitants ultérieurs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-2 pr-4">Sous-traitant</th>
                  <th className="py-2 pr-4">Pays</th>
                  <th className="py-2">Finalité</th>
                </tr>
              </thead>
              <tbody className="text-slate-200">
                <tr className="border-b border-slate-900">
                  <td className="py-3 pr-4 font-semibold">Anthropic PBC</td>
                  <td className="py-3 pr-4">États-Unis</td>
                  <td className="py-3">Modèle Claude pour génération de texte (emails, CR)</td>
                </tr>
                <tr className="border-b border-slate-900">
                  <td className="py-3 pr-4 font-semibold">Microsoft Ireland</td>
                  <td className="py-3 pr-4">Irlande</td>
                  <td className="py-3">Graph API (Outlook, Teams, Calendar, OneDrive)</td>
                </tr>
                <tr className="border-b border-slate-900">
                  <td className="py-3 pr-4 font-semibold">Voyage AI, Inc.</td>
                  <td className="py-3 pr-4">États-Unis</td>
                  <td className="py-3">Embeddings pour la mémoire contextuelle RAG</td>
                </tr>
                <tr className="border-b border-slate-900">
                  <td className="py-3 pr-4 font-semibold">Stripe Payments Europe</td>
                  <td className="py-3 pr-4">Irlande</td>
                  <td className="py-3">Traitement des paiements par carte bancaire</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-semibold">Hébergeur VPS</td>
                  <td className="py-3 pr-4">France / UE</td>
                  <td className="py-3">Hébergement des serveurs applicatifs et bases</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-sm text-slate-400">
            Les transferts vers les États-Unis (Anthropic, Voyage) sont encadrés par
            des Clauses Contractuelles Types adoptées par la Commission européenne
            (décision 2021/914) et par des DPA spécifiques. Aucune donnée sensible
            ne transite vers un pays ne bénéficiant pas de garanties appropriées.
          </p>
        </Section>

        <Section title="Contact & signalement">
          <p className="text-slate-300">
            Pour toute question relative à la sécurité de Secretary, ou pour
            signaler une vulnérabilité potentielle :
          </p>
          <ul className="mt-4 space-y-2 text-slate-200">
            <li>
              <strong>Sécurité générale</strong> :{" "}
              <a href="mailto:security@meoxa.app" className="text-sky-400">
                security@meoxa.app
              </a>
            </li>
            <li>
              <strong>Délégué à la protection des données</strong> :{" "}
              <a href="mailto:dpo@meoxa.app" className="text-sky-400">
                dpo@meoxa.app
              </a>
            </li>
            <li>
              <strong>Contact général</strong> :{" "}
              <a href="mailto:contact@meoxa.app" className="text-sky-400">
                contact@meoxa.app
              </a>
            </li>
          </ul>
          <p className="mt-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400">
            <strong className="text-slate-200">Disclosure responsable</strong> : si
            tu identifies une vulnérabilité, écris à security@meoxa.app avant
            toute publication. Nous nous engageons à te répondre sous 48 h et à
            publier un correctif sous 30 jours maximum.
          </p>
        </Section>

        <footer className="mt-16 border-t border-slate-800 pt-6 text-sm text-slate-500">
          <Link href="/" className="hover:text-slate-300">
            ← Retour à l'accueil
          </Link>
          {" · "}
          <Link href="/legal/confidentialite" className="hover:text-slate-300">
            Politique de confidentialité
          </Link>
          {" · "}
          <Link href="/legal/cgv" className="hover:text-slate-300">
            CGV
          </Link>
        </footer>
      </main>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-12">
      <h2 className="text-2xl font-bold text-white">{title}</h2>
      <div className="mt-6 space-y-5">{children}</div>
    </section>
  );
}

function Item({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
      <h3 className="font-semibold text-white">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-300">{text}</p>
    </div>
  );
}
