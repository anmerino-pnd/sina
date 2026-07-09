import { apiFetch } from "@/lib/api/client";
import type { CatalogoResponse } from "@/lib/types";

/** Catálogo estado → municipios. Cambia rara vez; cachear con staleTime alto. */
export function obtenerCatalogo(): Promise<CatalogoResponse> {
  return apiFetch<CatalogoResponse>("/catalogo");
}
