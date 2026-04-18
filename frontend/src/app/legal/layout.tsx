import Link from "next/link";

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
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

      <div className="mx-auto max-w-3xl px-6 py-16">
        <aside className="mb-8 flex flex-wrap gap-3 text-xs">
          <LegalLink href="/legal/mentions-legales" label="Mentions légales" />
          <LegalLink href="/legal/cgv" label="CGV" />
          <LegalLink href="/legal/confidentialite" label="Confidentialité" />
          <LegalLink href="/legal/cookies" label="Cookies" />
        </aside>
        <article className="prose prose-invert prose-slate max-w-none prose-headings:text-white prose-strong:text-white prose-a:text-sky-400">
          {children}
        </article>
        <footer className="mt-16 border-t border-slate-800 pt-6 text-xs text-slate-500">
          <Link href="/" className="hover:text-slate-300">
            ← Retour à l'accueil
          </Link>
        </footer>
      </div>
    </div>
  );
}

function LegalLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="rounded-full border border-slate-800 bg-slate-900/50 px-3 py-1 text-slate-300 hover:border-slate-600 hover:text-white"
    >
      {label}
    </Link>
  );
}
