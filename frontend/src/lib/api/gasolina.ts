import { apiFetch } from "@/lib/api/client";
import type { GasolinaResponse } from "@/lib/types";

export function obtenerGasolina(
  estado: string,
  municipio: string,
): Promise<GasolinaResponse> {
  const qs = new URLSearchParams({ estado, municipio });
  return apiFetch<GasolinaResponse>(`/gasolina?${qs}`);
}
