import { apiFetch } from "@/lib/api/client";
import type { SupermercadosResponse } from "@/lib/types";

export interface FiltrosSupermercado {
  q?: string;
  tienda?: string;
  departamento?: string;
  categoria?: string;
  limit?: number;
}

export function buscarProductos(
  filtros: FiltrosSupermercado,
): Promise<SupermercadosResponse> {
  const qs = new URLSearchParams();
  if (filtros.q) qs.set("q", filtros.q);
  if (filtros.tienda) qs.set("tienda", filtros.tienda);
  if (filtros.departamento) qs.set("departamento", filtros.departamento);
  if (filtros.categoria) qs.set("categoria", filtros.categoria);
  if (filtros.limit) qs.set("limit", String(filtros.limit));
  return apiFetch<SupermercadosResponse>(`/supermercados?${qs}`);
}
