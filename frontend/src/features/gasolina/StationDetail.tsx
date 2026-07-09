import { CategoryBadge } from "@/components/data/CategoryBadge";
import { formatearPesos } from "@/lib/format";
import { urlComoLlegar } from "@/lib/geo";
import type { Categoria } from "@/lib/precios";
import type { EstacionGasolina } from "@/lib/types";

interface Props {
  estacion: EstacionGasolina | null;
  categoria: Categoria | null;
  distanciaKm: number | null;
  esBase: boolean;
  onFijarBase: () => void;
}

function PrecioFila({ label, valor }: { label: string; valor: number | null }) {
  return (
    <div className="flex items-baseline justify-between border-t border-sand-100 py-1.5">
      <span className="text-sm text-ink-500">{label}</span>
      <span className={`tabular font-semibold ${valor == null ? "text-ink-500" : "text-ink-900"}`}>
        {valor == null ? "N/D" : formatearPesos(valor)}
      </span>
    </div>
  );
}

export function StationDetail({
  estacion,
  categoria,
  distanciaKm,
  esBase,
  onFijarBase,
}: Props) {
  if (!estacion) {
    return (
      <div className="rounded-[var(--radius-card)] border border-dashed border-sand-300 bg-surface/60 p-6 text-center text-sm text-ink-500">
        Selecciona una gasolinera en el mapa o el ranking para ver su detalle.
      </div>
    );
  }

  return (
    <div className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg text-ink-900">{estacion.nombre || "—"}</h3>
          <p className="mt-0.5 text-sm text-ink-500">
            {estacion.direccion || "Sin dirección registrada"}
          </p>
        </div>
        {categoria && <CategoryBadge categoria={categoria} />}
      </div>

      {distanciaKm != null && (
        <p className="mt-2 text-xs text-ink-500">
          A {distanciaKm.toFixed(1)} km de tu punto
        </p>
      )}

      <div className="mt-3">
        <PrecioFila label="Magna" valor={estacion.magna} />
        <PrecioFila label="Premium" valor={estacion.premium} />
        <PrecioFila label="Diésel" valor={estacion.diesel} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {estacion.latitud != null && estacion.longitud != null && (
          <a
            href={urlComoLlegar(estacion.latitud, estacion.longitud)}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Cómo llegar
          </a>
        )}
        <button
          onClick={onFijarBase}
          className={[
            "rounded-full border px-4 py-2 text-sm font-semibold",
            esBase
              ? "border-brand-600 bg-brand-50 text-brand-700"
              : "border-sand-300 bg-surface text-ink-700 hover:bg-sand-100",
          ].join(" ")}
        >
          {esBase ? "Base de comparación" : "Fijar como base"}
        </button>
      </div>
    </div>
  );
}
