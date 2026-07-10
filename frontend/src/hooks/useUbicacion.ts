import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";

const KEY = "sina.ubicacion";

type Clave = "estado" | "municipio" | "localidad";
// Además de los nombres, cacheamos las coordenadas del usuario (si las compartió)
// para las consultas de cercanía. Se comparten entre Gasolina y Chat.
export type Ubicacion = Partial<Record<Clave, string>> & {
  lat?: number;
  lng?: number;
  ts?: number; // epoch ms de la última captura de coordenadas
};

export function leerUbicacion(): Ubicacion {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Ubicacion) : {};
  } catch {
    return {};
  }
}

function guardar(u: Ubicacion): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(u));
  } catch {
    /* almacenamiento no disponible */
  }
}

/** Cachea las coordenadas del usuario (fuente única compartida Gasolina ↔ Chat). */
export function guardarCoordsUsuario(lat: number, lng: number): void {
  guardar({ ...leerUbicacion(), lat, lng, ts: Date.now() });
}

const leer = leerUbicacion;

/**
 * Sincroniza los parámetros de ubicación con localStorage para que la selección
 * sobreviva al cambiar de pestaña. La URL manda al cargar (enlaces compartibles);
 * si viene vacía, se hidrata desde lo último elegido.
 */
export function useUbicacionSync(claves: Clave[]): void {
  const [params, setParams] = useSearchParams();
  const hidratado = useRef(false);

  // Hidratar una sola vez si la URL no trae estado.
  useEffect(() => {
    if (hidratado.current) return;
    hidratado.current = true;
    if (params.get("estado")) return;

    const u = leer();
    if (!u.estado) return;
    const next = new URLSearchParams();
    for (const k of claves) {
      if (u[k]) next.set(k, u[k]!);
    }
    if ([...next.keys()].length) setParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persistir cambios de la URL.
  useEffect(() => {
    const previo = leer();
    const merged: Ubicacion = { ...previo };
    for (const k of claves) {
      const v = params.get(k);
      if (v) merged[k] = v;
    }
    // Si esta vista cambió el municipio y no gestiona localidad, la localidad
    // guardada queda obsoleta → se limpia.
    const mun = params.get("municipio");
    if (
      claves.includes("municipio") &&
      !claves.includes("localidad") &&
      mun &&
      mun !== previo.municipio
    ) {
      delete merged.localidad;
    }
    guardar(merged);
  }, [params, claves]);
}
