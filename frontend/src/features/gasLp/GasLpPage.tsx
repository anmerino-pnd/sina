import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AutocompleteInput, type Opcion } from "@/components/data/AutocompleteInput";
import { KpiRow } from "@/components/data/KpiRow";
import { RankingTable, type FilaRanking } from "@/components/data/RankingTable";
import { FreshnessBadge } from "@/components/data/FreshnessBadge";
import { Pill, PillGroup } from "@/components/ui/Pill";
import {
  ComingSoonState,
  ErrorState,
  Skeleton,
  WelcomeState,
} from "@/components/ui/States";
import { useCatalogo } from "@/hooks/useCatalogo";
import { useUbicacionSync } from "@/hooks/useUbicacion";
import { ApiError } from "@/lib/api/client";
import { obtenerGasLpPorIds, obtenerLocalidades } from "@/lib/api/gasLp";
import { capitalizar, formatearPesos } from "@/lib/format";
import { categorizar, type Categoria } from "@/lib/precios";
import type { GasLPItem } from "@/lib/types";

import { ProviderDetail } from "@/features/gasLp/ProviderDetail";

const idDe = (i: GasLPItem) =>
  `${i.numero_permiso}|${i.tipo}|${i.capacidad_recipiente ?? ""}`;

const CLAVES_UBIC: ("estado" | "municipio" | "localidad")[] = [
  "estado",
  "municipio",
  "localidad",
];

export default function GasLpPage() {
  const [params, setParams] = useSearchParams();
  const estadoSel = params.get("estado") ?? "";
  const munSel = params.get("municipio") ?? "";
  const locSel = params.get("localidad") ?? "";

  useUbicacionSync(CLAVES_UBIC);
  const { data: catalogo } = useCatalogo();

  const [tipoSel, setTipoSel] = useState<"recipiente" | "autotanque">("recipiente");
  const [capSel, setCapSel] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // ── Localidades (dan también entidad_id / municipio_id) ──
  const locQuery = useQuery({
    queryKey: ["gaslp-localidades", estadoSel, munSel],
    queryFn: () => obtenerLocalidades(estadoSel, munSel),
    enabled: !!estadoSel && !!munSel,
    staleTime: Infinity,
  });

  const localidadId = useMemo(
    () => locQuery.data?.localidades.find((l) => l.nombre === locSel)?.id ?? null,
    [locQuery.data, locSel],
  );

  const dataQuery = useQuery({
    queryKey: [
      "gaslp",
      locQuery.data?.entidad_id,
      locQuery.data?.municipio_id,
      localidadId,
    ],
    queryFn: () =>
      obtenerGasLpPorIds(
        locQuery.data!.entidad_id,
        locQuery.data!.municipio_id,
        localidadId!,
      ),
    enabled: !!locQuery.data && localidadId != null,
    staleTime: 30 * 60_000,
  });

  // Reinicia filtros al cambiar de localidad.
  useEffect(() => {
    setTipoSel("recipiente");
    setCapSel(null);
    setSelectedId(null);
  }, [locSel, estadoSel, munSel]);

  // ── Opciones de selectores ─────────────────────────────
  const opcionesEstado: Opcion[] = useMemo(
    () => Object.keys(catalogo ?? {}).sort().map((e) => ({ value: e, label: e })),
    [catalogo],
  );
  const opcionesMunicipio: Opcion[] = useMemo(
    () => (catalogo?.[estadoSel] ?? []).map((m) => ({ value: m, label: m })),
    [catalogo, estadoSel],
  );
  const opcionesLocalidad: Opcion[] = useMemo(
    () =>
      (locQuery.data?.localidades ?? []).map((l) => ({
        value: l.nombre,
        label: l.nombre,
      })),
    [locQuery.data],
  );

  // ── Derivaciones ───────────────────────────────────────
  const datos: GasLPItem[] = useMemo(() => {
    if (!dataQuery.data) return [];
    return [...dataQuery.data.autotanques, ...dataQuery.data.recipientes];
  }, [dataQuery.data]);

  const porTipo = useMemo(
    () => datos.filter((d) => d.tipo === tipoSel),
    [datos, tipoSel],
  );

  const capsDisponibles = useMemo(() => {
    if (tipoSel !== "recipiente") return [];
    const s = new Set<number>();
    porTipo.forEach((d) => {
      if (d.capacidad_recipiente != null) s.add(d.capacidad_recipiente);
    });
    return [...s].sort((a, b) => a - b);
  }, [porTipo, tipoSel]);

  const capEfectiva =
    tipoSel === "recipiente" ? (capSel ?? capsDisponibles[0] ?? null) : null;

  const filtrados = useMemo(() => {
    if (tipoSel === "recipiente" && capEfectiva != null) {
      return porTipo.filter((d) => d.capacidad_recipiente === capEfectiva);
    }
    return porTipo;
  }, [porTipo, tipoSel, capEfectiva]);

  const precios = useMemo(
    () => filtrados.map((d) => d.precio).filter((v) => v != null && !Number.isNaN(v)),
    [filtrados],
  );

  const kpis = useMemo(() => {
    if (precios.length === 0) return null;
    const suma = precios.reduce((a, b) => a + b, 0);
    return {
      prom: suma / precios.length,
      min: Math.min(...precios),
      max: Math.max(...precios),
      count: precios.length,
    };
  }, [precios]);

  const ranking: FilaRanking[] = useMemo(
    () =>
      [...filtrados]
        .sort((a, b) => a.precio - b.precio)
        .slice(0, 10)
        .map((d) => {
          const nombre = d.marca_comercial || d.numero_permiso || "—";
          return {
            id: idDe(d),
            nombre: nombre.length > 28 ? nombre.slice(0, 26) + "…" : nombre,
            precio: d.precio,
            categoria: categorizar(d.precio, precios),
            sufijoPrecio: " /kg",
          };
        }),
    [filtrados, precios],
  );

  const seleccionado = useMemo(
    () => filtrados.find((d) => idDe(d) === selectedId) ?? null,
    [filtrados, selectedId],
  );
  const seleccionadoCat: Categoria | null = seleccionado
    ? categorizar(seleccionado.precio, precios)
    : null;

  // ── Handlers ───────────────────────────────────────────
  const sinLocalidad = !estadoSel || !munSel || !locSel;
  const cargando =
    locQuery.isLoading ||
    (!!locSel && localidadId != null && dataQuery.isLoading);
  const noEncontrado =
    dataQuery.error instanceof ApiError &&
    (dataQuery.error.status === 404 || dataQuery.error.status === 400);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-3xl md:text-4xl">Gas LP</h1>
      <p className="mt-1 text-ink-700">
        Compara el precio por kilo de cada permisionario en tu localidad.
      </p>

      {/* Cascada estado → municipio → localidad */}
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <AutocompleteInput
          label="Estado"
          placeholder="Escribe tu estado"
          opciones={opcionesEstado}
          valorTexto={estadoSel ? capitalizar(estadoSel) : ""}
          onSelect={(o) => setParams({ estado: o.value })}
        />
        <AutocompleteInput
          label="Municipio"
          placeholder={estadoSel ? "Escribe tu municipio" : "Elige un estado"}
          opciones={opcionesMunicipio}
          valorTexto={munSel ? capitalizar(munSel) : ""}
          onSelect={(o) => setParams({ estado: estadoSel, municipio: o.value })}
          disabled={!estadoSel}
        />
        <AutocompleteInput
          label="Localidad"
          placeholder={munSel ? "Escribe tu localidad" : "Elige un municipio"}
          opciones={opcionesLocalidad}
          valorTexto={locSel ? capitalizar(locSel) : ""}
          onSelect={(o) =>
            setParams({ estado: estadoSel, municipio: munSel, localidad: o.value })
          }
          disabled={!munSel}
          cargando={locQuery.isLoading}
        />
      </div>

      <div className="mt-8">
        {sinLocalidad ? (
          <WelcomeState
            titulo="Elige una localidad"
            detalle="Selecciona estado, municipio y localidad para ver los precios de Gas LP."
          />
        ) : cargando ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-56" />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
            <Skeleton className="h-72" />
          </div>
        ) : noEncontrado || (dataQuery.data && datos.length === 0) ? (
          <ComingSoonState
            titulo="Aún no tenemos datos aquí"
            detalle={`De momento no hay precios de Gas LP para ${capitalizar(locSel)}, ${capitalizar(munSel)}.`}
          />
        ) : dataQuery.isError ? (
          <ErrorState
            titulo="No se pudieron cargar los precios"
            detalle="La fuente puede estar temporalmente fuera de servicio. Intenta de nuevo."
            accion={
              <button
                onClick={() => dataQuery.refetch()}
                className="rounded-full bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Reintentar
              </button>
            }
          />
        ) : (
          dataQuery.data && (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <PillGroup label="Tipo">
                  <Pill
                    activo={tipoSel === "recipiente"}
                    onClick={() => {
                      setTipoSel("recipiente");
                      setCapSel(null);
                      setSelectedId(null);
                    }}
                  >
                    Recipientes
                  </Pill>
                  <Pill
                    activo={tipoSel === "autotanque"}
                    onClick={() => {
                      setTipoSel("autotanque");
                      setCapSel(null);
                      setSelectedId(null);
                    }}
                  >
                    Autotanques
                  </Pill>
                </PillGroup>
                <FreshnessBadge
                  fuente={dataQuery.data.fuente}
                  fecha={dataQuery.data.fecha_datos}
                />
              </div>

              {tipoSel === "recipiente" && capsDisponibles.length > 0 && (
                <PillGroup label="Capacidad">
                  {capsDisponibles.map((c) => (
                    <Pill
                      key={c}
                      activo={capEfectiva === c}
                      onClick={() => {
                        setCapSel(c);
                        setSelectedId(null);
                      }}
                    >
                      {c} kg
                    </Pill>
                  ))}
                </PillGroup>
              )}

              <KpiRow
                items={[
                  { label: "Promedio", valor: kpis ? formatearPesos(kpis.prom) : "—" },
                  { label: "Mínimo", valor: kpis ? formatearPesos(kpis.min) : "—", tono: "low" },
                  { label: "Máximo", valor: kpis ? formatearPesos(kpis.max) : "—", tono: "high" },
                  { label: "Proveedores", valor: kpis ? String(kpis.count) : "0" },
                ]}
              />

              <div className="grid gap-5 lg:grid-cols-2">
                <RankingTable
                  titulo={`Proveedores · ${tipoSel === "autotanque" ? "Autotanques" : "Recipientes"}`}
                  filas={ranking}
                  seleccionadoId={selectedId}
                  onSelect={setSelectedId}
                  vacioTexto="Sin datos para este filtro"
                />
                <ProviderDetail item={seleccionado} categoria={seleccionadoCat} />
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
