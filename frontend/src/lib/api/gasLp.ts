import { apiFetch } from "@/lib/api/client";
import type { GasLPResponse, LocalidadesResponse } from "@/lib/types";

export function obtenerLocalidades(
  estado: string,
  municipio: string,
): Promise<LocalidadesResponse> {
  const qs = new URLSearchParams({ estado, municipio });
  return apiFetch<LocalidadesResponse>(`/gas-lp/localidades?${qs}`);
}

export function obtenerGasLpPorIds(
  entidadId: number,
  municipioId: string,
  localidadId: number,
): Promise<GasLPResponse> {
  const qs = new URLSearchParams({
    entidad_id: String(entidadId),
    municipio_id: municipioId,
    localidad_id: String(localidadId),
  });
  return apiFetch<GasLPResponse>(`/gas-lp/by-ids?${qs}`);
}
