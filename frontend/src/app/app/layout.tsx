"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isDashboard = pathname === "/app";

  function logout() {
    document.cookie = "access_token=; max-age=0; path=/";
    router.replace("/login");
  }

  return (
    <>
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          {isDashboard ? (
            <Link
              href="/app"
              className="text-lg font-bold text-slate-100 hover:text-white"
            >
              meoxa
            </Link>
          ) : (
            <Link
              href="/app"
              className="text-sm text-slate-300 hover:text-white"
            >
              ← Tableau de bord
            </Link>
          )}
          <button
            onClick={logout}
            className="text-sm text-slate-400 hover:text-slate-200"
          >
            Se déconnecter
          </button>
        </div>
      </header>
      {children}
    </>
  );
}
