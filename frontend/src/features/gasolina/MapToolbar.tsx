import { useState } from "react";

import { COLOR_CATEGORIA, type Categoria } from "@/lib/precios";
import { IconCheck, IconPin, IconTarget } from "@/components/ui/icons";

const CATEGORIAS: Categoria[] = ["Barato", "Promedio", "Caro"];

interface Props {
  filtroCategoria: Categoria | null;
  onToggleFiltro: (c: Categoria) => void;
  modoFijar: boolean;
  tienePunto: boolean;
  onToggleFijar: () => void;
  onUbicarme: (lat: number, lng: number, esManual: boolean) => void;
  onQuitarPunto: () => void;
}

export function MapToolbar({
  filtroCategoria,
  onToggleFiltro,
  modoFijar,
  tienePunto,
  onToggleFijar,
  onUbicarme,
  onQuitarPunto,
}: Props) {
  const [buscando, setBuscando] = useState(false);

  function ubicarme() {
    if (!navigator.geolocation) {
      alert("Tu navegador no soporta geolocalización.");
      return;
    }
    setBuscando(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setBuscando(false);
        onUbicarme(pos.coords.latitude, pos.coords.longitude, false);
      },
      () => {
        setBuscando(false);
        alert('No se pudo obtener tu ubicación. Usa "Fijar punto" para colocarla manualmente.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  }

  const btn =
    "rounded-full border border-sand-300 bg-surface px-3 py-1.5 text-sm font-medium text-ink-700 hover:bg-sand-100";

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Leyenda clicable = filtro por categoría */}
      <div className="flex items-center gap-1">
        {CATEGORIAS.map((c) => {
          const activo = filtroCategoria === c;
          const opacado = filtroCategoria !== null && !activo;
          return (
            <button
              key={c}
              onClick={() => onToggleFiltro(c)}
              aria-pressed={activo}
              className={[
                "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-opacity",
                activo ? "bg-sand-100 text-ink-900" : "text-ink-700",
                opacado ? "opacity-40" : "",
              ].join(" ")}
            >
              <span
                className="inline-block size-2.5 rounded-full"
                style={{ background: COLOR_CATEGORIA[c] }}
                aria-hidden="true"
              />
              {c}
            </button>
          );
        })}
      </div>

      <div className="ml-auto flex flex-wrap items-center gap-2">
        <button className={`${btn} inline-flex items-center gap-1.5`} onClick={ubicarme} disabled={buscando}>
          <IconPin />
          {buscando ? "Buscando…" : "Mi ubicación"}
        </button>
        <button
          className={[
            btn,
            "inline-flex items-center gap-1.5",
            modoFijar ? "!border-brand-600 !bg-brand-600 !text-white" : "",
          ].join(" ")}
          onClick={onToggleFijar}
          aria-pressed={modoFijar}
        >
          {modoFijar ? <IconCheck /> : <IconTarget />}
          {modoFijar ? "Haz clic en el mapa" : "Fijar punto"}
        </button>
        {tienePunto && (
          <button className={btn} onClick={onQuitarPunto}>
            Quitar punto
          </button>
        )}
      </div>
    </div>
  );
}
