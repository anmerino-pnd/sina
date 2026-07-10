import { CategoryBadge } from "@/components/data/CategoryBadge";
import { formatearPesos } from "@/lib/format";
import { urlComoLlegar } from "@/lib/geo";
import type { Categoria } from "@/lib/precios";
import type { EstacionGasolina, TipoCombustible } from "@/lib/types";

interface Props {
  estacion: EstacionGasolina | null;
  categoria: Categoria | null;
  /** Combustible activo (pill de arriba): se resalta en el panel de precios. */
  fuel: TipoCombustible;
  distanciaKm: number | null;
  esBase: boolean;
  onFijarBase: () => void;
}

const ETIQUETA_FUEL: Record<TipoCombustible, string> = {
  magna: "Magna",
  premium: "Premium",
  diesel: "Diésel",
};
const ORDEN_FUEL: TipoCombustible[] = ["magna", "premium", "diesel"];

export function StationDetail({
  estacion,
  categoria,
  fuel,
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
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
            Estación seleccionada
          </p>
          <h3 className="mt-0.5 truncate text-lg text-ink-900">{estacion.nombre || "—"}</h3>
          <p className="mt-0.5 truncate text-sm text-ink-500">
            {estacion.direccion || "Sin dirección registrada"}
          </p>
        </div>
        {categoria && <CategoryBadge categoria={categoria} />}
      </div>

      {distanciaKm != null && (
        <span className="mt-3 inline-flex items-center rounded-full bg-sand-100 px-2.5 py-1 text-xs font-medium text-ink-700">
          A {distanciaKm.toFixed(1)} km de tu punto
        </span>
      )}

      {/* Precios como panel segmentado; el combustible activo se destaca en neutro. */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        {ORDEN_FUEL.map((f) => {
          const activo = f === fuel;
          const valor = estacion[f];
          return (
            <div
              key={f}
              className={[
                "rounded-xl px-2 py-2.5 text-center transition-colors",
                activo ? "bg-sand-100" : "bg-sand-50",
              ].join(" ")}
            >
              <span className="block text-[11px] font-medium uppercase tracking-wide text-ink-500">
                {ETIQUETA_FUEL[f]}
              </span>
              <span
                className={`tabular mt-0.5 block text-sm font-semibold ${
                  valor == null ? "text-ink-500" : activo ? "text-ink-900" : "text-ink-700"
                }`}
              >
                {valor == null ? "N/D" : formatearPesos(valor)}
              </span>
            </div>
          );
        })}
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
