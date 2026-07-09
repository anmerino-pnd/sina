import { formatearPesos } from "@/lib/format";

interface Props {
  tipo: "litros" | "pesos";
  monto: number;
  onTipo: (t: "litros" | "pesos") => void;
  onMonto: (n: number) => void;

  baseNombre: string;
  basePrecio: number;
  esBase: boolean; // true = base fijada por el usuario; false = usa la más barata
  onResetBase: () => void;

  // Estación de comparación: la seleccionada por el usuario o la más cara.
  refNombre: string | null;
  refPrecio: number | null;
  refEsSeleccion: boolean;
}

export function FuelCalculator({
  tipo,
  monto,
  onTipo,
  onMonto,
  baseNombre,
  basePrecio,
  esBase,
  onResetBase,
  refNombre,
  refPrecio,
  refEsSeleccion,
}: Props) {
  const m = monto > 0 ? monto : tipo === "litros" ? 35 : 300;
  const litrosBase = tipo === "litros" ? m : m / basePrecio;
  const costoBase = tipo === "litros" ? m * basePrecio : m;

  // Comparación contra la referencia (más cara o seleccionada).
  let comp: { costo: string; ahorro: string; pct: string } | null = null;
  if (refPrecio != null && refNombre != null && refPrecio !== basePrecio) {
    if (tipo === "litros") {
      const costoRef = m * refPrecio;
      const ahorro = costoRef - costoBase;
      comp = {
        costo: formatearPesos(costoRef),
        ahorro: formatearPesos(ahorro),
        pct: `${((ahorro / costoBase) * 100).toFixed(1)}%`,
      };
    } else {
      const litrosRef = m / refPrecio;
      const extra = litrosBase - litrosRef;
      comp = {
        costo: `${litrosRef.toFixed(2)} L`,
        ahorro: `${extra.toFixed(2)} L`,
        pct: `${((extra / litrosRef) * 100).toFixed(1)}%`,
      };
    }
  }

  const tab = (activo: boolean) =>
    [
      "flex-1 rounded-lg py-1.5 text-sm font-medium transition-colors",
      activo ? "bg-brand-600 text-white" : "text-ink-700 hover:bg-sand-100",
    ].join(" ");

  const valorBase =
    tipo === "litros" ? formatearPesos(costoBase) : `${litrosBase.toFixed(2)} L`;

  return (
    <div className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-5 shadow-[var(--shadow-card)]">
      <h3 className="text-base font-semibold text-ink-900">Calculadora de ahorro</h3>

      <div className="mt-3 flex gap-1 rounded-xl bg-sand-100 p-1">
        <button className={tab(tipo === "litros")} onClick={() => onTipo("litros")}>
          Por litros
        </button>
        <button className={tab(tipo === "pesos")} onClick={() => onTipo("pesos")}>
          Por pesos
        </button>
      </div>

      <label className="mt-3 block">
        <span className="sr-only">{tipo === "litros" ? "Litros" : "Pesos"}</span>
        <div className="flex items-center gap-2 rounded-xl border border-sand-300 px-3 py-2">
          <span className="text-ink-500">{tipo === "litros" ? "L" : "$"}</span>
          <input
            type="number"
            min={0}
            value={monto || ""}
            placeholder={tipo === "litros" ? "35" : "300"}
            onChange={(e) => onMonto(parseFloat(e.target.value) || 0)}
            className="tabular w-full bg-transparent text-ink-900 outline-none"
          />
        </div>
      </label>

      {/* Base */}
      <div className="mt-4 rounded-xl bg-sand-50 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-price-low">
            {esBase ? "Tu base" : "La más barata"}
          </span>
          {esBase && (
            <button
              onClick={onResetBase}
              className="text-xs font-semibold text-ink-500 hover:text-ink-700"
            >
              Quitar base
            </button>
          )}
        </div>
        <p className="tabular mt-1 text-2xl font-semibold text-ink-900">{valorBase}</p>
        <p className="truncate text-sm text-ink-500">{baseNombre}</p>
      </div>

      {/* Comparación */}
      {comp && refNombre ? (
        <div className="mt-2 rounded-xl border border-sand-200 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">
              {refEsSeleccion ? "Estación seleccionada" : "La más cara"}
            </span>
            <span className="tabular text-sm font-medium text-ink-700">{comp.costo}</span>
          </div>
          <p className="truncate text-sm text-ink-500">{refNombre}</p>
          <p className="tabular mt-2 text-sm font-semibold text-price-high">
            {tipo === "litros"
              ? `Ahorras ${comp.ahorro} (${comp.pct})`
              : `Rinde ${comp.ahorro} más (${comp.pct})`}
          </p>
        </div>
      ) : (
        <p className="mt-2 text-xs text-ink-500">
          Selecciona una estación en el mapa o el ranking para compararla con la más barata.
        </p>
      )}
    </div>
  );
}
