import { useState } from "react";
import { NavLink } from "react-router-dom";

import { SinaMark } from "@/components/layout/SinaMark";
import { useAuth } from "@/components/auth/AuthProvider";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { AccountMenu } from "@/components/auth/AccountMenu";
import { ThemeToggle } from "@/components/theme/ThemeProvider";

interface Seccion {
  to: string;
  label: string;
  pronto?: boolean;
}

const SECCIONES: Seccion[] = [
  { to: "/gasolina", label: "Gasolina" },
  { to: "/gas-lp", label: "Gas LP" },
  { to: "/supermercados", label: "Supermercados" },
  { to: "/chat", label: "Chat" },
];

function linkClases({ isActive }: { isActive: boolean }): string {
  return [
    "relative rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
    isActive
      ? "bg-brand-50 text-brand-700 dark:text-brand-200"
      : "text-ink-700 hover:bg-sand-100",
  ].join(" ");
}

export function Navbar() {
  const { user, status } = useAuth();
  const [menuMovil, setMenuMovil] = useState(false);

  return (
    <header className="glass sticky top-0 z-40 border-b border-sand-200">
      <nav className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
        <NavLink to="/" className="flex items-center gap-2">
          <SinaMark className="size-9" />
          <span className="font-display text-xl font-semibold tracking-tight text-ink-900">
            Sina
          </span>
        </NavLink>

        <div className="hidden items-center gap-1 md:flex">
          {SECCIONES.map((s) => (
            <NavLink key={s.to} to={s.to} className={linkClases}>
              {s.label}
              {s.pronto && (
                <span className="ml-1.5 rounded-full bg-flare-500/12 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-flare-600 dark:text-flare-400">
                  pronto
                </span>
              )}
            </NavLink>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          {status === "ready" &&
            (user ? <AccountMenu /> : <GoogleSignInButton />)}
          <button
            className="rounded-lg p-2 text-ink-700 hover:bg-sand-100 md:hidden"
            aria-label="Abrir menú"
            aria-expanded={menuMovil}
            onClick={() => setMenuMovil((v) => !v)}
          >
            <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
              <path
                d="M4 6h16M4 12h16M4 18h16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </nav>

      {menuMovil && (
        <div className="border-t border-sand-200 bg-sand-50 px-4 py-2 md:hidden">
          {SECCIONES.map((s) => (
            <NavLink
              key={s.to}
              to={s.to}
              onClick={() => setMenuMovil(false)}
              className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-sand-100"
            >
              {s.label}
              {s.pronto && (
                <span className="rounded-full bg-flare-500/12 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-flare-600 dark:text-flare-400">
                  pronto
                </span>
              )}
            </NavLink>
          ))}
        </div>
      )}
    </header>
  );
}
