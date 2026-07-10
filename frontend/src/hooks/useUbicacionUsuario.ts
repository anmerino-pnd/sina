import { useCallback, useState } from "react";

import { guardarCoordsUsuario, leerUbicacion, type Ubicacion } from "@/hooks/useUbicacion";

// Coordenadas más viejas que esto se consideran "para refrescar" (no bloquea el uso).
const FRESCURA_MS = 1000 * 60 * 60; // 1 hora

interface UbicacionUsuario {
  /** Nombres (estado/municipio/localidad) elegidos en los dashboards. */
  ubicacion: Ubicacion;
  /** ¿Hay coordenadas cacheadas? */
  tieneCoords: boolean;
  /** ¿Las coordenadas son recientes? */
  coordsFrescas: boolean;
  buscando: boolean;
  error: string | null;
  /** Pide geolocalización al navegador (solo por acción explícita) y la cachea. */
  pedirUbicacion: () => void;
}

/**
 * Captura y cachea la ubicación del usuario de forma NO intrusiva: solo pide
 * geolocalización cuando el usuario lo solicita (botón), y guarda el resultado
 * en `localStorage["sina.ubicacion"]` — la misma fuente que usa Gasolina, así el
 * "cerca de mí" se comparte entre el chat y el mapa sin volver a preguntar.
 */
export function useUbicacionUsuario(): UbicacionUsuario {
  const [ubicacion, setUbicacion] = useState<Ubicacion>(() => leerUbicacion());
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pedirUbicacion = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Tu navegador no soporta geolocalización.");
      return;
    }
    setBuscando(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        guardarCoordsUsuario(pos.coords.latitude, pos.coords.longitude);
        setUbicacion(leerUbicacion());
        setBuscando(false);
      },
      () => {
        setBuscando(false);
        setError("No se pudo obtener tu ubicación.");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  }, []);

  const tieneCoords = ubicacion.lat != null && ubicacion.lng != null;
  const coordsFrescas = tieneCoords && !!ubicacion.ts && Date.now() - ubicacion.ts < FRESCURA_MS;

  return { ubicacion, tieneCoords, coordsFrescas, buscando, error, pedirUbicacion };
}
