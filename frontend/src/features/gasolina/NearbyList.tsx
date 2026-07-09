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
  onSelect: (numero: string) => void;
}

export function NearbyList({ items, titulo, onSelect }: Props) {
  return (
    <div className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-4 shadow-[var(--shadow-card)]">
      <h3 className="mb-2 text-base font-semibold text-ink-900">{titulo}</h3>
      <ul className="divide-y divide-sand-100">
        {items.map((c) => (
          <li key={c.numero}>
            <button
              onClick={() => onSelect(c.numero)}
              className="flex w-full items-center justify-between gap-3 py-2.5 text-left hover:bg-sand-50"
            >
              <span className="min-w-0">
                <span className="block truncate font-medium text-ink-900">
                  {c.nombre}
                </span>
                <span className="text-xs text-ink-500">
                  {c.dist.toFixed(1)} km · {c.categoria}
                </span>
              </span>
              <span className={`tabular font-semibold ${CLASE_PRECIO[c.categoria]}`}>
                {formatearPesos(c.precio)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
