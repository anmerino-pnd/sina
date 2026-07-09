import { useEffect, useId, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { fijarUsername } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";

const REGLA = /^[a-z0-9_]{3,30}$/;

export function UsernameModal({ onClose }: { onClose: () => void }) {
  const { user, setUser } = useAuth();
  const [valor, setValor] = useState(user?.username ?? "");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    const limpio = valor.trim().toLowerCase();
    if (!REGLA.test(limpio)) {
      setError("Usa 3–30 caracteres: minúsculas, números o guion bajo.");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      const actualizado = await fijarUsername(limpio);
      setUser(actualizado);
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Ese nombre de usuario ya está en uso.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Nombre de usuario no válido.");
      } else {
        setError("No se pudo guardar. Intenta de nuevo.");
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        className="w-full max-w-md rounded-2xl bg-surface p-6 shadow-[var(--shadow-card)]"
      >
        <h2 id={titleId} className="text-xl">
          Elige tu nombre de usuario
        </h2>
        <p id={descId} className="mt-1 text-sm text-ink-500">
          Es opcional y distinto de tu cuenta de Google. Puedes cambiarlo después.
        </p>
        <form onSubmit={guardar} className="mt-4">
          <label htmlFor="username-input" className="sr-only">
            Nombre de usuario
          </label>
          <input
            id="username-input"
            ref={inputRef}
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder="p. ej. familia_ramirez"
            autoComplete="off"
            spellCheck={false}
            className="w-full rounded-xl border border-sand-300 bg-sand-50 px-4 py-2.5 text-ink-900 placeholder:text-ink-500/60"
          />
          {error && (
            <p className="mt-2 text-sm text-price-high" role="alert">
              {error}
            </p>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full px-4 py-2 text-sm font-medium text-ink-700 hover:bg-sand-100"
            >
              Ahora no
            </button>
            <button
              type="submit"
              disabled={guardando}
              className="rounded-full bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {guardando ? "Guardando…" : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
