import { CLASE_PRECIO, type Categoria } from "@/lib/precios";
import { formatearPesos } from "@/lib/format";

export interface Cercana {
  numero: string;
  nombre: string;
  precio: number;
  categoria: Categoria;
  dist: number;
}

interface Props {
  items: Cercana[];
  titulo: string;
  seleccionadoId: string | null;
  onSelect: (numero: string) => void;
}

/**
 * Estaciones cercanas: lista vertical de tarjetas independientes bajo la
 * calculadora / estación seleccionada. La lista se limita en alto y hace scroll
 * propio, así no aparecen todas de golpe (se revelan al desplazar).
 */
export function NearbyList({ items, titulo, seleccionadoId, onSelect }: Props) {
  return (
    <div className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-4 shadow-[var(--shadow-card)]">
      <h3 className="mb-3 text-base font-semibold text-ink-900">{titulo}</h3>
      <ul className="flex max-h-72 flex-col gap-2 overflow-y-auto pr-1">
        {items.map((c) => {
          const sel = c.numero === seleccionadoId;
          return (
            <li key={c.numero}>
              <button
                onClick={() => onSelect(c.numero)}
                aria-pressed={sel}
                className={[
                  "flex w-full items-center justify-between gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors",
                  sel
                    ? "border-brand-200 bg-brand-50 ring-1 ring-brand-200"
                    : "border-sand-200 hover:bg-sand-50",
                ].join(" ")}
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-ink-900">
                    {c.nombre}
                  </span>
                  <span className="text-xs text-ink-500">
                    {c.dist.toFixed(1)} km · {c.categoria}
                  </span>
                </span>
                <span className={`tabular shrink-0 font-semibold ${CLASE_PRECIO[c.categoria]}`}>
                  {formatearPesos(c.precio)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
