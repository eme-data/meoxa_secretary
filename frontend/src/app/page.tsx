import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-10 shadow-xl">
        <h1 className="text-4xl font-bold text-white">Pack Secrétariat</h1>
        <p className="mt-3 text-lg text-slate-300">
          Automatisation emails, comptes-rendus de réunions, agenda.
        </p>
        <div className="mt-8 text-5xl font-bold text-white">
          1 490 € <span className="text-xl text-sky-400">HT</span>
        </div>
        <ul className="mt-8 space-y-2 text-slate-200">
          <li>✓ Intégration clé en main</li>
          <li>✓ Configuration sur vos outils</li>
        </ul>
        <div className="mt-10 flex gap-4">
          <Link
            href="/login"
            className="rounded-lg bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-dark"
          >
            Se connecter
          </Link>
          <Link
            href="/signup"
            className="rounded-lg border border-slate-700 px-5 py-3 font-semibold text-slate-200 hover:bg-slate-800"
          >
            Créer un compte
          </Link>
        </div>
      </section>
    </main>
  );
}
