import { CategoryBadge } from "@/components/data/CategoryBadge";
import { formatearPesos, formatearFecha } from "@/lib/format";
import type { Categoria } from "@/lib/precios";
import type { GasLPItem } from "@/lib/types";

interface Props {
  item: GasLPItem | null;
  categoria: Categoria | null;
}

export function ProviderDetail({ item, categoria }: Props) {
  if (!item) {
    return (
      <div className="rounded-[var(--radius-card)] border border-dashed border-sand-300 bg-surface/60 p-6 text-center text-sm text-ink-500">
        Selecciona un proveedor del ranking para ver su detalle.
      </div>
    );
  }

  const tipoLabel = item.tipo === "autotanque" ? "Autotanque" : "Recipiente";

  return (
    <div className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg text-ink-900">
            {item.marca_comercial || "Sin marca comercial"}
          </h3>
          <p className="mt-0.5 text-sm text-ink-500">
            Permiso {item.numero_permiso || "—"}
          </p>
        </div>
        {categoria && <CategoryBadge categoria={categoria} />}
      </div>

      <p className="tabular mt-4 text-3xl font-semibold text-ink-900">
        {formatearPesos(item.precio)}
        <span className="text-base font-normal text-ink-500"> / kg</span>
      </p>

      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-sage-500/12 px-2.5 py-1 font-semibold text-sage-600">
          {tipoLabel}
        </span>
        {item.capacidad_recipiente != null && (
          <span className="rounded-full bg-brand-50 px-2.5 py-1 font-semibold text-brand-700">
            {item.capacidad_recipiente} kg
          </span>
        )}
        <span className="rounded-full bg-sand-100 px-2.5 py-1 text-ink-500">
          Actualizado el {formatearFecha(item.fecha_extraccion)}
        </span>
        {item.vigente && (
          <span className="rounded-full bg-price-low/12 px-2.5 py-1 font-semibold text-price-low">
            Vigente
          </span>
        )}
      </div>
    </div>
  );
}
