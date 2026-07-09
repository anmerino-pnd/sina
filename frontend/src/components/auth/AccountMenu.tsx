import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { UsernameModal } from "@/components/auth/UsernameModal";

export function AccountMenu() {
  const { user, signOut } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [modal, setModal] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [abierto]);

  if (!user) return null;

  const nombreVisible = user.username ?? user.nombre ?? "Mi cuenta";
  const inicial = nombreVisible.charAt(0).toUpperCase();

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setAbierto((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={abierto}
        className="flex items-center gap-2 rounded-full border border-sand-300 bg-surface/70 py-1 pl-1 pr-3 text-sm font-medium text-ink-700 hover:bg-sand-100"
      >
        <span className="grid size-7 place-items-center rounded-full bg-brand-600 text-xs font-semibold text-white">
          {inicial}
        </span>
        <span className="max-w-28 truncate">{nombreVisible}</span>
      </button>

      {abierto && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-56 overflow-hidden rounded-xl border border-sand-200 bg-surface shadow-[var(--shadow-card)]"
        >
          <div className="border-b border-sand-100 px-4 py-3">
            <p className="truncate text-sm font-semibold text-ink-900">
              {nombreVisible}
            </p>
            {user.needs_username && (
              <p className="mt-0.5 text-xs text-flare-600 dark:text-flare-400">
                Aún no eliges nombre de usuario
              </p>
            )}
          </div>
          <button
            role="menuitem"
            onClick={() => {
              setModal(true);
              setAbierto(false);
            }}
            className="block w-full px-4 py-2.5 text-left text-sm text-ink-700 hover:bg-sand-50"
          >
            Editar nombre de usuario
          </button>
          <button
            role="menuitem"
            onClick={() => {
              setAbierto(false);
              void signOut();
            }}
            className="block w-full px-4 py-2.5 text-left text-sm text-ink-700 hover:bg-sand-50"
          >
            Cerrar sesión
          </button>
        </div>
      )}

      {modal && <UsernameModal onClose={() => setModal(false)} />}
    </div>
  );
}
