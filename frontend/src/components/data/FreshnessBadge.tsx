import { formatearFecha } from "@/lib/format";
import type { Fuente } from "@/lib/types";

interface Props {
  fuente?: Fuente;
  fecha: string | null;
}

/** Indica origen y fecha del dato; avisa (no bloquea) si la caché venció. */
export function FreshnessBadge({ fuente, fecha }: Props) {
  const vencido = fuente === "cache_vencido";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span
        className={[
          "inline-block size-2 rounded-full",
          vencido ? "bg-price-mid" : "bg-price-low",
        ].join(" ")}
        aria-hidden="true"
      />
      <span className={vencido ? "text-price-mid" : "text-ink-500"}>
        {vencido
          ? `Datos con fecha ${formatearFecha(fecha)} (puede haber cambios recientes)`
          : `Actualizado el ${formatearFecha(fecha)}`}
      </span>
    </div>
  );
}
