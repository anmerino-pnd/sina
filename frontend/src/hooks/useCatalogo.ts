import { useQuery } from "@tanstack/react-query";

import { obtenerCatalogo } from "@/lib/api/catalogo";

/** Catálogo estado → municipios. Cambia rara vez; se cachea indefinidamente. */
export function useCatalogo() {
  return useQuery({
    queryKey: ["catalogo"],
    queryFn: obtenerCatalogo,
    staleTime: Infinity,
    select: (data) => data.estados,
  });
}
