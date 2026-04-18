import Link from "next/link";

// Pour mettre la vidéo : remplacer par l'URL iframe YouTube, Vimeo ou Loom
// YouTube   : https://www.youtube.com/embed/VIDEO_ID
// Vimeo     : https://player.vimeo.com/video/VIDEO_ID
// Loom      : https://www.loom.com/embed/VIDEO_ID
// Laisser vide = placeholder "Démo à venir"
const DEMO_VIDEO_URL = "";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Nav />
      <Hero />
      <VideoSection />
      <PainSection />
      <FeaturesSection />
      <HowItWorksSection />
      <SecuritySection />
      <PricingSection />
      <FaqSection />
      <FinalCta />
      <Footer />
    </div>
  );
}

// ============================================================================
// Navigation fixe en haut
// ============================================================================
function Nav() {
  return (
    <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-xl font-bold tracking-tight">
          meoxa<span className="text-brand">.</span>
        </Link>
        <div className="hidden gap-8 text-sm text-slate-300 md:flex">
          <a href="#fonctionnalites" className="hover:text-white">Fonctionnalités</a>
          <a href="#comment" className="hover:text-white">Comment ça marche</a>
          <a href="#securite" className="hover:text-white">Sécurité</a>
          <a href="#tarifs" className="hover:text-white">Tarifs</a>
          <a href="#faq" className="hover:text-white">FAQ</a>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-semibold text-slate-300 hover:text-white"
          >
            Se connecter
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-dark"
          >
            Démarrer
          </Link>
        </div>
      </div>
    </nav>
  );
}

// ============================================================================
// Hero
// ============================================================================
function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20 text-center md:py-32">
      <div className="mb-6 inline-block rounded-full border border-sky-700/50 bg-sky-900/20 px-4 py-1 text-xs font-semibold text-sky-300">
        Pour les PME sous Microsoft 365
      </div>
      <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-6xl">
        Ton assistant de direction
        <br />
        <span className="bg-gradient-to-r from-sky-400 to-cyan-300 bg-clip-text text-transparent">
          automatique dans Microsoft 365
        </span>
      </h1>
      <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300 md:text-xl">
        meoxa lit tes emails et prépare tes réponses dans ton style. Il écoute tes
        réunions Teams et rédige le compte-rendu. Il propose des créneaux depuis
        ton calendrier. Tout en français, sans changer d'outil.
      </p>
      <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <Link
          href="/signup"
          className="rounded-lg bg-brand px-8 py-4 text-base font-semibold text-white shadow-lg shadow-sky-900/30 hover:bg-brand-dark"
        >
          Démarrer — 1 490 € HT / an
        </Link>
        <a
          href="#demo"
          className="rounded-lg border border-slate-700 px-8 py-4 text-base font-semibold text-slate-200 hover:bg-slate-800"
        >
          Voir la démo (2 min)
        </a>
      </div>
      <p className="mt-6 text-sm text-slate-500">
        Hébergé en France · Conforme RGPD · Résiliable à tout moment
      </p>
    </section>
  );
}

// ============================================================================
// Vidéo de démonstration
// ============================================================================
function VideoSection() {
  return (
    <section id="demo" className="mx-auto max-w-5xl px-6 pb-20">
      <div className="aspect-video overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl">
        {DEMO_VIDEO_URL ? (
          <iframe
            src={DEMO_VIDEO_URL}
            title="Démo meoxa"
            className="h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-3 text-slate-500">
            <div className="rounded-full border border-slate-700 bg-slate-800 p-6">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-10 w-10 text-sky-400"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-slate-300">
              Démo vidéo disponible prochainement
            </p>
            <p className="max-w-md text-center text-sm">
              Pour une démonstration live, contactez-nous directement.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

// ============================================================================
// Problème / pain point
// ============================================================================
function PainSection() {
  return (
    <section className="border-y border-slate-800 bg-slate-900/30 py-20">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="text-center text-3xl font-bold md:text-4xl">
          Un dirigeant de PME perd <span className="text-sky-400">2 heures par jour</span>
          <br />
          sur des tâches à faible valeur ajoutée
        </h2>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          <PainCard
            title="Emails qui s'accumulent"
            text={`Entre 50 et 150 emails par jour. Chacun demande 3 minutes de réflexion, même pour écrire "OK, je valide".`}
          />
          <PainCard
            title="Réunions sans trace"
            text="Les décisions prises en réunion Teams se perdent. Les actions ne sont pas tracées. Le CR n'est jamais écrit."
          />
          <PainCard
            title="Agenda mal géré"
            text="Trouver un créneau qui convient à tout le monde prend 10 échanges. On oublie la pause déjeuner."
          />
        </div>
        <p className="mt-12 text-center text-lg text-slate-400">
          Embaucher un(e) assistant(e) coûte <strong className="text-white">30 à 40 k€/an chargés</strong>.
          Automatiser ce travail coûte <strong className="text-white">1 490 €/an</strong>.
        </p>
      </div>
    </section>
  );
}

function PainCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-3 text-sm leading-relaxed text-slate-400">{text}</p>
    </div>
  );
}

// ============================================================================
// Fonctionnalités (3 piliers)
// ============================================================================
function FeaturesSection() {
  return (
    <section id="fonctionnalites" className="mx-auto max-w-6xl px-6 py-20">
      <h2 className="text-center text-3xl font-bold md:text-4xl">
        Trois piliers qui te rendent du temps
      </h2>
      <p className="mx-auto mt-4 max-w-2xl text-center text-slate-400">
        Chaque fonctionnalité s'intègre dans les outils que tu utilises déjà.
        Tu ne changes rien à ta façon de travailler — meoxa travaille à côté.
      </p>

      <div className="mt-16 grid gap-8 md:grid-cols-3">
        <FeatureCard
          number="01"
          title="Emails : il rédige, tu relis"
          bullets={[
            "Analyse chaque email reçu dans Outlook",
            "Rédige un brouillon de réponse dans ton style",
            "Apparaît directement dans tes Brouillons Outlook",
            "Tu valides en 30 secondes, ou tu édites",
          ]}
          gain="Gain typique : 3 à 5 h / semaine"
        />
        <FeatureCard
          number="02"
          title="Réunions Teams : il écoute, résume, envoie"
          bullets={[
            "Capte l'enregistrement Teams automatiquement",
            "Produit un CR structuré (résumé, décisions, actions)",
            "Envoie le CR par mail à l'organisateur",
            "Crée les tâches extraites dans Microsoft Planner",
          ]}
          gain="Gain typique : 30 à 60 min par réunion"
        />
        <FeatureCard
          number="03"
          title="Agenda : il propose, tu arbitres"
          bullets={[
            "Analyse ton calendrier Outlook",
            "Propose des créneaux respectant tes horaires",
            "Crée le lien Teams automatiquement",
            "Respecte ta pause déjeuner et tes jours off",
          ]}
          gain="Gain typique : 1 h / semaine"
        />
      </div>
    </section>
  );
}

function FeatureCard({
  number,
  title,
  bullets,
  gain,
}: {
  number: string;
  title: string;
  bullets: string[];
  gain: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8">
      <div className="font-mono text-sm text-sky-400">{number}</div>
      <h3 className="mt-3 text-xl font-bold">{title}</h3>
      <ul className="mt-4 space-y-2 text-sm text-slate-300">
        {bullets.map((b) => (
          <li key={b} className="flex items-start gap-2">
            <span className="mt-1 text-emerald-400">✓</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>
      <p className="mt-6 rounded-lg bg-slate-950 px-4 py-2 text-xs font-semibold text-sky-300">
        {gain}
      </p>
    </div>
  );
}

// ============================================================================
// Comment ça marche
// ============================================================================
function HowItWorksSection() {
  return (
    <section id="comment" className="border-y border-slate-800 bg-slate-900/30 py-20">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="text-center text-3xl font-bold md:text-4xl">
          Opérationnel en 48 heures
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-slate-400">
          Un onboarding guidé de 5 minutes, puis meoxa se met au travail.
          Aucune formation nécessaire pour tes équipes.
        </p>

        <ol className="mt-12 space-y-8">
          <Step
            n={1}
            title="Tu souscris au Pack Secrétariat"
            text="1 490 € HT / an, paiement sécurisé Stripe. Démarrage immédiat, résiliable à tout moment depuis ton espace."
          />
          <Step
            n={2}
            title="Tu connectes ton Microsoft 365"
            text="Un seul clic pour autoriser l'accès à Outlook, Calendar et OneDrive. Tu gardes le contrôle — tu peux révoquer à tout moment."
          />
          <Step
            n={3}
            title="meoxa analyse tes 30 derniers jours"
            text="Pour apprendre ton ton, ton vocabulaire et le style de tes réponses. Les brouillons générés seront pertinents dès le premier jour."
          />
          <Step
            n={4}
            title="Tu actives l'enregistrement auto sur Teams"
            text="Une case à cocher dans l'admin Teams. Dès la prochaine réunion, tu reçois automatiquement le compte-rendu."
          />
          <Step
            n={5}
            title="Tu gagnes du temps, dès le premier jour"
            text="Les brouillons d'emails apparaissent dans ton Outlook. Les CR arrivent par mail après chaque réunion. Tu relis, tu valides, tu envoies."
          />
        </ol>
      </div>
    </section>
  );
}

function Step({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <li className="flex gap-6">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand font-bold text-white">
        {n}
      </div>
      <div>
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="mt-1 text-slate-400">{text}</p>
      </div>
    </li>
  );
}

// ============================================================================
// Sécurité
// ============================================================================
function SecuritySection() {
  return (
    <section id="securite" className="mx-auto max-w-6xl px-6 py-20">
      <h2 className="text-center text-3xl font-bold md:text-4xl">
        Tes données restent les tiennes
      </h2>
      <p className="mx-auto mt-4 max-w-2xl text-center text-slate-400">
        meoxa est conçu autour de la confidentialité. Rien ne sort de l'Union
        européenne, tout est chiffré, tout est auditable.
      </p>
      <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <SecurityCard title="Hébergement UE" text="Serveur dédié en France, opéré par MDO Services. Aucune donnée ne transite hors UE sans clauses contractuelles types." />
        <SecurityCard title="Chiffrement Fernet" text="Tous les secrets applicatifs (API keys, tokens OAuth) sont chiffrés au repos. TLS 1.3 sur toutes les communications externes." />
        <SecurityCard title="Isolation multi-tenant" text="PostgreSQL Row-Level Security garantit l'isolation au niveau base de données. Aucune requête cross-tenant n'est techniquement possible." />
        <SecurityCard title="RGPD natif" text="Export en un clic, droit à l'oubli, contrat de sous-traitance (DPA) généré automatiquement, rétention configurable." />
        <SecurityCard title="2FA TOTP" text="Double authentification disponible pour tous les utilisateurs. Codes de secours à usage unique." />
        <SecurityCard title="Journal d'audit" text="Toutes les actions sensibles sont tracées : login, changement de config, accès aux données, modifications de rôles." />
        <SecurityCard title="Sauvegardes off-site" text="Backup PostgreSQL quotidien chiffré, rétention 14 jours, copie hors site. Tests de restauration réguliers." />
        <SecurityCard title="Observabilité" text="Monitoring d'erreurs self-hosted (GlitchTip). Tu peux auditer tout ce qui se passe sur ton tenant depuis ton interface admin." />
      </div>
    </section>
  );
}

function SecurityCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-slate-400">{text}</p>
    </div>
  );
}

// ============================================================================
// Tarifs
// ============================================================================
function PricingSection() {
  return (
    <section id="tarifs" className="border-y border-slate-800 bg-slate-900/30 py-20">
      <div className="mx-auto max-w-3xl px-6">
        <h2 className="text-center text-3xl font-bold md:text-4xl">Un prix simple, sans surprise</h2>
        <p className="mx-auto mt-4 max-w-xl text-center text-slate-400">
          Pas de palier "Entreprise" à négocier, pas de surtaxe à l'usage, pas
          d'engagement pluriannuel.
        </p>

        <div className="mt-12 overflow-hidden rounded-3xl border border-sky-700/50 bg-gradient-to-b from-sky-900/20 to-slate-900/60 shadow-2xl">
          <div className="p-8 md:p-12">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold">Pack Secrétariat</h3>
              <div className="rounded-full bg-emerald-900/40 px-3 py-1 text-xs font-semibold text-emerald-300">
                Offre de lancement
              </div>
            </div>

            <div className="mt-6">
              <div className="flex items-baseline gap-2">
                <span className="text-6xl font-bold text-white">1 490 €</span>
                <span className="text-xl text-sky-400">HT / an</span>
              </div>
              <p className="mt-2 text-sm text-slate-400">
                Soit <strong className="text-slate-200">~124 € / mois</strong>,
                renouvelé automatiquement. Résiliable à tout moment depuis ton espace.
              </p>
            </div>

            <ul className="mt-8 space-y-3 text-slate-200">
              {[
                "Intégration clé en main à Microsoft 365",
                "Utilisateurs illimités dans ton organisation",
                "Import de tes 30 derniers jours d'emails pour apprentissage",
                "Brouillons d'emails, CR de réunions, agenda",
                "Actions des réunions poussées dans Microsoft Planner",
                "Notifications Slack ou Teams configurables",
                "Export RGPD complet, DPA fourni",
                "2FA, audit log, chiffrement au repos",
                "Hébergement France, souveraineté garantie",
                "Support par email et Teams",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-0.5 text-emerald-400">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            <div className="mt-10 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/signup"
                className="flex-1 rounded-lg bg-brand px-6 py-4 text-center text-base font-semibold text-white shadow-lg shadow-sky-900/30 hover:bg-brand-dark"
              >
                Démarrer maintenant
              </Link>
              <a
                href="mailto:mathieu@mdoservices.fr?subject=Démo Pack Secrétariat"
                className="flex-1 rounded-lg border border-slate-700 px-6 py-4 text-center text-base font-semibold text-slate-200 hover:bg-slate-800"
              >
                Demander une démo
              </a>
            </div>
          </div>
        </div>

        <p className="mt-8 text-center text-sm text-slate-500">
          Le coût API Claude est inclus dans l'abonnement, dans la limite d'un usage
          raisonnable (jusqu'à 10 000 emails et 50 réunions par mois). Au-delà, un
          palier Entreprise est disponible sur devis.
        </p>
      </div>
    </section>
  );
}

// ============================================================================
// FAQ
// ============================================================================
function FaqSection() {
  const faqs = [
    {
      q: "Qui lit mes emails ?",
      a: "meoxa lit tes emails — c'est lui qui génère les brouillons. Les données sont envoyées à Anthropic (Claude) pour la génération du texte, avec un contrat de sous-traitance en place. Aucun humain de MDO Services n'a accès à tes emails. Tout est chiffré en transit et au repos.",
    },
    {
      q: "Est-ce que ça envoie des emails sans mon accord ?",
      a: "Non, jamais. meoxa rédige des brouillons. Rien n'est envoyé tant que tu ne cliques pas sur Envoyer dans ton Outlook. Tu gardes le contrôle total.",
    },
    {
      q: "Faut-il Teams Premium ?",
      a: "Non. meoxa fonctionne avec Office 365 Business Basic et Standard. Il exploite simplement les enregistrements Teams que tu actives normalement dans tes réunions — pas besoin de l'add-on Premium.",
    },
    {
      q: "Mes équipes doivent-elles se former ?",
      a: "Non. Les brouillons apparaissent directement dans Outlook, les CR arrivent par mail. Tes équipes continuent à utiliser leurs outils habituels.",
    },
    {
      q: "Comment se passe la résiliation ?",
      a: "Depuis ton espace Facturation, un clic pour annuler. L'abonnement reste actif jusqu'à la fin de la période annuelle payée. Tu peux exporter toutes tes données avant départ via l'onglet Organisation.",
    },
    {
      q: "Mes clients concurrents auront-ils accès à mes données ?",
      a: "Impossible techniquement. Chaque client a ses données isolées au niveau base de données (PostgreSQL Row-Level Security). Même le code applicatif ne peut pas lire au-delà de ton tenant.",
    },
    {
      q: "Ça marche avec Google Workspace ?",
      a: "Pas encore. meoxa est aujourd'hui focalisé sur Microsoft 365. Le support Google est sur notre roadmap.",
    },
    {
      q: "Qui est derrière meoxa ?",
      a: "MDO Services, société française indépendante fondée par Mathieu d'Oliveira. Pas de fonds, pas de data broker derrière — juste un éditeur qui fait son métier.",
    },
  ];

  return (
    <section id="faq" className="mx-auto max-w-3xl px-6 py-20">
      <h2 className="text-center text-3xl font-bold md:text-4xl">Questions fréquentes</h2>
      <div className="mt-12 space-y-3">
        {faqs.map((f) => (
          <details
            key={f.q}
            className="group rounded-xl border border-slate-800 bg-slate-900/60 p-5 open:bg-slate-900"
          >
            <summary className="flex cursor-pointer items-center justify-between font-semibold">
              {f.q}
              <span className="text-sky-400 transition group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

// ============================================================================
// CTA final
// ============================================================================
function FinalCta() {
  return (
    <section className="border-y border-slate-800 bg-gradient-to-br from-sky-900/30 via-slate-950 to-slate-950 py-24">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <h2 className="text-3xl font-bold md:text-4xl">
          Reprends 10 heures par semaine
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-slate-300">
          Moins cher qu'une semaine d'intérim, installé en 48 h,
          résiliable à tout moment.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/signup"
            className="rounded-lg bg-brand px-8 py-4 text-base font-semibold text-white shadow-lg shadow-sky-900/30 hover:bg-brand-dark"
          >
            Démarrer — 1 490 € HT / an
          </Link>
          <a
            href="mailto:mathieu@mdoservices.fr?subject=Démo Pack Secrétariat"
            className="rounded-lg border border-slate-700 px-8 py-4 text-base font-semibold text-slate-200 hover:bg-slate-800"
          >
            Parler à un humain
          </a>
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// Footer
// ============================================================================
function Footer() {
  return (
    <footer className="bg-slate-950 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-6 md:flex-row">
        <div>
          <div className="text-xl font-bold">
            meoxa<span className="text-brand">.</span>
          </div>
          <p className="mt-2 text-sm text-slate-500">
            Édité par MDO Services — {new Date().getFullYear()}
          </p>
        </div>
        <div className="flex flex-wrap gap-6 text-sm text-slate-400">
          <Link href="/login" className="hover:text-white">
            Se connecter
          </Link>
          <Link href="/signup" className="hover:text-white">
            Créer un compte
          </Link>
          <a href="mailto:mathieu@mdoservices.fr" className="hover:text-white">
            Contact
          </a>
          <a href="#securite" className="hover:text-white">
            Sécurité
          </a>
          <a href="#tarifs" className="hover:text-white">
            Tarifs
          </a>
        </div>
      </div>
    </footer>
  );
}
