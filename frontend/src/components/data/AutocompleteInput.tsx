import { useEffect, useId, useMemo, useRef, useState } from "react";

import { capitalizar } from "@/lib/format";

export interface Opcion {
  value: string;
  label: string;
}

interface Props {
  label: string;
  placeholder: string;
  opciones: Opcion[];
  /** Etiqueta del valor elegido (vacío si nada elegido). */
  valorTexto: string;
  onSelect: (opcion: Opcion) => void;
  disabled?: boolean;
  /** Mensaje mientras cargan opciones (p. ej. localidades). */
  cargando?: boolean;
}

// Prioriza coincidencias por prefijo, luego por substring (igual que el JS actual).
function filtrar(opciones: Opcion[], q: string): Opcion[] {
  const t = q.toLowerCase().trim();
  if (!t) return opciones;
  const prefix = opciones.filter((o) => o.label.toLowerCase().startsWith(t));
  const contains = opciones.filter(
    (o) => !o.label.toLowerCase().startsWith(t) && o.label.toLowerCase().includes(t),
  );
  return [...prefix, ...contains];
}

/**
 * Combobox accesible con autocompletado. Reemplaza el patrón
 * filtrarEstados/renderDrop/abrirDrop del JS actual, con teclado y ARIA.
 */
export function AutocompleteInput({
  label,
  placeholder,
  opciones,
  valorTexto,
  onSelect,
  disabled,
  cargando,
}: Props) {
  const [texto, setTexto] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [resaltado, setResaltado] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  // Cuando cambia el valor elegido desde fuera, refleja su etiqueta.
  useEffect(() => {
    setTexto(valorTexto);
  }, [valorTexto]);

  const filtradas = useMemo(
    () => filtrar(opciones, texto === valorTexto ? "" : texto),
    [opciones, texto, valorTexto],
  );

  useEffect(() => {
    if (!abierto) return;
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [abierto]);

  function elegir(o: Opcion) {
    onSelect(o);
    setTexto(o.label);
    setAbierto(false);
  }

  function onKey(e: React.KeyboardEvent) {
    if (!abierto && (e.key === "ArrowDown" || e.key === "Enter")) {
      setAbierto(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setResaltado((i) => Math.min(i + 1, filtradas.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setResaltado((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtradas[resaltado]) elegir(filtradas[resaltado]);
    } else if (e.key === "Escape") {
      setAbierto(false);
    }
  }

  return (
    <div ref={wrapRef} className="relative">
      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-ink-500">
        {label}
      </label>
      <input
        role="combobox"
        aria-expanded={abierto}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        spellCheck={false}
        disabled={disabled}
        value={texto}
        placeholder={placeholder}
        onChange={(e) => {
          setTexto(e.target.value);
          setAbierto(true);
          setResaltado(0);
        }}
        onFocus={() => setAbierto(true)}
        onKeyDown={onKey}
        className="w-full rounded-xl border border-sand-300 bg-surface px-4 py-2.5 text-ink-900 placeholder:text-ink-500/60 disabled:cursor-not-allowed disabled:bg-sand-100 disabled:text-ink-500"
      />
      {abierto && !disabled && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-sand-200 bg-surface py-1 shadow-[var(--shadow-card)]"
        >
          {cargando ? (
            <li className="px-4 py-2 text-sm text-ink-500">Cargando…</li>
          ) : filtradas.length === 0 ? (
            <li className="px-4 py-2 text-sm text-ink-500">Sin resultados</li>
          ) : (
            filtradas.map((o, i) => (
              <li
                key={o.value}
                role="option"
                aria-selected={i === resaltado}
                onMouseDown={(e) => {
                  e.preventDefault();
                  elegir(o);
                }}
                onMouseEnter={() => setResaltado(i)}
                className={[
                  "cursor-pointer px-4 py-2 text-sm",
                  i === resaltado
                    ? "bg-brand-50 text-brand-700 dark:bg-sand-200 dark:text-ink-900"
                    : "text-ink-700",
                ].join(" ")}
              >
                {capitalizar(o.label)}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
