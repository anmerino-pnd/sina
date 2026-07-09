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
}

export function RankingTable({
  titulo,
  filas,
  seleccionadoId,
  onSelect,
  vacioTexto = "Sin datos",
}: Props) {
  return (
    <div className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-4 shadow-[var(--shadow-card)]">
      <h3 className="mb-3 text-base font-semibold text-ink-900">{titulo}</h3>
      {filas.length === 0 ? (
        <p className="py-6 text-center text-sm text-ink-500">{vacioTexto}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-ink-500">
                <th className="w-8 pb-2 font-semibold">#</th>
                <th className="pb-2 font-semibold">Nombre</th>
                <th className="pb-2 text-right font-semibold">Precio</th>
                <th className="pb-2 pl-3 font-semibold">Categoría</th>
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
                      "cursor-pointer border-t border-sand-100 transition-colors",
                      sel ? "bg-brand-50" : "hover:bg-sand-50",
                    ].join(" ")}
                  >
                    <td className="py-2.5 font-semibold text-ink-500">{i + 1}</td>
                    <td className="py-2.5 pr-2 font-medium text-ink-900">
                      {f.nombre}
                    </td>
                    <td
                      className={`tabular py-2.5 text-right font-semibold ${CLASE_PRECIO[f.categoria]}`}
                    >
                      {formatearPesos(f.precio)}
                      {f.sufijoPrecio && (
                        <span className="text-xs font-normal text-ink-500">
                          {f.sufijoPrecio}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pl-3">
                      <CategoryBadge categoria={f.categoria} />
                    </td>
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
