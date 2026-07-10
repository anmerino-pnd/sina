import { CategoryBadge } from "@/components/data/CategoryBadge";
import { CLASE_PRECIO, type Categoria } from "@/lib/precios";
import { formatearPesos } from "@/lib/format";

export interface FilaRanking {
  id: string;
  nombre: string;
  precio: number;
  categoria: Categoria;
  sufijoPrecio?: string;
}

interface Props {
  titulo: string;
  filas: FilaRanking[];
  seleccionadoId: string | null;
  onSelect: (id: string) => void;
  vacioTexto?: string;
  /** El color del precio ya comunica la categoría; ocultar la columna evita redundancia. */
  mostrarCategoria?: boolean;
  /** Limita el alto y hace scroll interno (para dejar sitio a otra card debajo). */
  compacto?: boolean;
}

export function RankingTable({
  titulo,
  filas,
  seleccionadoId,
  onSelect,
  vacioTexto = "Sin datos",
  mostrarCategoria = true,
  compacto = false,
}: Props) {
  return (
    <div className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-4 shadow-[var(--shadow-card)]">
      <h3 className="mb-3 text-base font-semibold text-ink-900">{titulo}</h3>
      {filas.length === 0 ? (
        <p className="py-6 text-center text-sm text-ink-500">{vacioTexto}</p>
      ) : (
        <div className={compacto ? "max-h-72 overflow-y-auto overflow-x-hidden pr-1" : "overflow-x-auto"}>
          {/* border-separate + spacing permite fondos redondeados por fila:
              el resaltado (hover/seleccionado) es una "pill", no una banda a sangre. */}
          <table className="w-full border-separate border-spacing-y-1 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-ink-500">
                <th className="sticky top-0 z-10 w-8 bg-surface px-2 pb-1 font-semibold">#</th>
                <th className="sticky top-0 z-10 bg-surface pb-1 font-semibold">Nombre</th>
                <th className="sticky top-0 z-10 bg-surface px-2 pb-1 text-right font-semibold">
                  Precio
                </th>
                {mostrarCategoria && (
                  <th className="sticky top-0 z-10 bg-surface px-2 pb-1 font-semibold">Categoría</th>
                )}
              </tr>
            </thead>
            <tbody>
              {filas.map((f, i) => {
                const sel = f.id === seleccionadoId;
                return (
                  <tr
                    key={f.id}
                    onClick={() => onSelect(f.id)}
                    className={[
                      "cursor-pointer transition-colors",
                      sel ? "bg-brand-50" : "hover:bg-sand-50",
                    ].join(" ")}
                  >
                    <td className="rounded-l-xl py-2.5 pl-3 pr-1 font-semibold text-ink-500">
                      {i + 1}
                    </td>
                    <td className="py-2.5 pr-2 font-medium text-ink-900">
                      {f.nombre}
                    </td>
                    <td
                      className={`tabular px-2 py-2.5 text-right font-semibold ${CLASE_PRECIO[f.categoria]} ${
                        mostrarCategoria ? "" : "rounded-r-xl"
                      }`}
                    >
                      {formatearPesos(f.precio)}
                      {f.sufijoPrecio && (
                        <span className="text-xs font-normal text-ink-500">
                          {f.sufijoPrecio}
                        </span>
                      )}
                    </td>
                    {mostrarCategoria && (
                      <td className="rounded-r-xl py-2.5 pl-1 pr-3">
                        <CategoryBadge categoria={f.categoria} />
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
