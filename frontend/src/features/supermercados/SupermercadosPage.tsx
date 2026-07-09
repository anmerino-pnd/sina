import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { Pill, PillGroup } from "@/components/ui/Pill";
import { ComingSoonState, ErrorState, Skeleton } from "@/components/ui/States";
import { buscarProductos } from "@/lib/api/supermercados";
import { formatearPesos } from "@/lib/format";

export default function SupermercadosPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const tienda = params.get("tienda") ?? "";

  const [texto, setTexto] = useState(q);

  // Debounce del texto → parámetro de búsqueda (300ms).
  useEffect(() => {
    const t = setTimeout(() => {
      const next = new URLSearchParams(params);
      if (texto) next.set("q", texto);
      else next.delete("q");
      // Evita reescribir si no cambió (previene loops).
      if ((next.get("q") ?? "") !== q) setParams(next, { replace: true });
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto]);

  const query = useQuery({
    queryKey: ["supermercados", q, tienda],
    queryFn: () =>
      buscarProductos({ q: q || undefined, tienda: tienda || undefined, limit: 30 }),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

  // Chips de tienda derivados de los resultados actuales.
  const tiendas = useMemo(() => {
    const s = new Set<string>();
    (query.data?.datos ?? []).forEach((p) => p.tienda && s.add(p.tienda));
    if (tienda) s.add(tienda);
    return [...s].sort();
  }, [query.data, tienda]);

  function setTienda(t: string) {
    const next = new URLSearchParams(params);
    if (t) next.set("tienda", t);
    else next.delete("tienda");
    setParams(next, { replace: true });
  }

  const productos = query.data?.datos ?? [];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-3xl md:text-4xl">Supermercados</h1>
      <p className="mt-1 text-ink-700">
        Busca un producto de la despensa y descubre dónde sale más barato.
      </p>

      <div className="mt-5 max-w-xl">
        <label htmlFor="buscar-producto" className="sr-only">
          Buscar producto
        </label>
        <input
          id="buscar-producto"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="p. ej. leche, huevo, aceite…"
          className="w-full rounded-full border border-sand-300 bg-surface px-5 py-3 text-ink-900 placeholder:text-ink-500/60"
        />
      </div>

      {tiendas.length > 0 && (
        <div className="mt-4">
          <PillGroup label="Tienda">
            <Pill activo={tienda === ""} onClick={() => setTienda("")}>
              Todas
            </Pill>
            {tiendas.map((t) => (
              <Pill key={t} activo={tienda === t} onClick={() => setTienda(t)}>
                {t}
              </Pill>
            ))}
          </PillGroup>
        </div>
      )}

      <div className="mt-8">
        {query.isLoading ? (
          <div className="space-y-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : query.isError ? (
          <ErrorState
            titulo="No se pudo buscar"
            detalle="Intenta de nuevo en un momento."
            accion={
              <button
                onClick={() => query.refetch()}
                className="rounded-full bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Reintentar
              </button>
            }
          />
        ) : productos.length === 0 ? (
          <ComingSoonState
            titulo={q ? "Sin resultados" : "Empieza a buscar"}
            detalle={
              q
                ? `No encontramos productos para “${q}”. Prueba con otra palabra.`
                : "Escribe el nombre de un producto para comparar precios entre tiendas."
            }
          />
        ) : (
          <div className="overflow-x-auto rounded-[var(--radius-card)] border border-sand-200 bg-surface shadow-[var(--shadow-card)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-sand-100 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-4 py-3 font-semibold">Producto</th>
                  <th className="px-4 py-3 font-semibold">Tienda</th>
                  <th className="hidden px-4 py-3 font-semibold md:table-cell">Categoría</th>
                  <th className="px-4 py-3 text-right font-semibold">Precio</th>
                </tr>
              </thead>
              <tbody>
                {productos.map((p) => (
                  <tr key={p.pid} className="border-t border-sand-100 hover:bg-sand-50">
                    <td className="px-4 py-3 font-medium text-ink-900">{p.producto}</td>
                    <td className="px-4 py-3 text-ink-700">{p.tienda}</td>
                    <td className="hidden px-4 py-3 text-ink-500 md:table-cell">
                      {p.categoria ?? "—"}
                    </td>
                    <td className="tabular px-4 py-3 text-right font-semibold text-ink-900">
                      {formatearPesos(p.precio)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
