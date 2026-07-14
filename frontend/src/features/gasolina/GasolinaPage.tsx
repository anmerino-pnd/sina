import { Suspense, lazy, useCallback, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AutocompleteInput, type Opcion } from "@/components/data/AutocompleteInput";
import { KpiRow } from "@/components/data/KpiRow";
import { RankingTable, type FilaRanking } from "@/components/data/RankingTable";
import { FreshnessBadge } from "@/components/data/FreshnessBadge";
import {
  ComingSoonState,
  ErrorState,
  Skeleton,
  WelcomeState,
} from "@/components/ui/States";
import { useCatalogo } from "@/hooks/useCatalogo";
import { useUbicacionSync } from "@/hooks/useUbicacion";
import { ApiError } from "@/lib/api/client";
import { obtenerGasolina } from "@/lib/api/gasolina";
import { capitalizar, formatearPesos } from "@/lib/format";
import { distKm } from "@/lib/geo";
import { categorizar, type Categoria } from "@/lib/precios";
import type { EstacionGasolina, TipoCombustible } from "@/lib/types";

import { FuelPills } from "@/features/gasolina/FuelPills";
import { MapToolbar } from "@/features/gasolina/MapToolbar";
import { StationDetail } from "@/features/gasolina/StationDetail";
import { FuelCalculator } from "@/features/gasolina/FuelCalculator";
import { NearbyList, type Cercana } from "@/features/gasolina/NearbyList";
import { useGasolinaState } from "@/features/gasolina/useGasolinaState";
import type { MarcadorEstacion } from "@/features/gasolina/StationMap";

const StationMap = lazy(() => import("@/features/gasolina/StationMap"));

const FUELS: TipoCombustible[] = ["magna", "premium", "diesel"];
const CLAVES_UBIC: ("estado" | "municipio")[] = ["estado", "municipio"];

export default function GasolinaPage() {
  const [params, setParams] = useSearchParams();
  const estadoSel = params.get("estado") ?? "";
  const munSel = params.get("municipio") ?? "";

  useUbicacionSync(CLAVES_UBIC);
  const { data: catalogo } = useCatalogo();
  const [st, dispatch] = useGasolinaState();

  // Reinicia el estado de UI al cambiar de ubicación.
  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [estadoSel, munSel, dispatch]);

  // Callbacks estables para el mapa: permiten que los marcadores memoizados
  // no se re-rendericen en cada render de la página (dispatch es estable).
  const onSelectEstacion = useCallback(
    (n: string) => dispatch({ type: "SELECT", numero: n }),
    [dispatch],
  );
  const onDeselectEstacion = useCallback(() => dispatch({ type: "DESELECT" }), [dispatch]);
  const onFijarPunto = useCallback(
    (lat: number, lng: number) =>
      dispatch({ type: "SET_PUNTO", punto: { lat, lng, manual: true } }),
    [dispatch],
  );

  const query = useQuery({
    queryKey: ["gasolina", estadoSel, munSel],
    queryFn: () => obtenerGasolina(estadoSel, munSel),
    enabled: !!estadoSel && !!munSel,
    staleTime: 5 * 60_000,
  });

  const opcionesEstado: Opcion[] = useMemo(
    () =>
      Object.keys(catalogo ?? {})
        .sort()
        .map((e) => ({ value: e, label: e })),
    [catalogo],
  );
  const opcionesMunicipio: Opcion[] = useMemo(
    () => (catalogo?.[estadoSel] ?? []).map((m) => ({ value: m, label: m })),
    [catalogo, estadoSel],
  );

  // ── Derivaciones de datos ──────────────────────────────
  const estaciones = useMemo(
    () =>
      (query.data?.datos ?? []).filter(
        (e) => e.latitud != null && e.longitud != null,
      ),
    [query.data],
  );

  const preciosFuel = useMemo(
    () =>
      estaciones
        .map((e) => e[st.fuel])
        .filter((v): v is number => v != null && !Number.isNaN(v)),
    [estaciones, st.fuel],
  );

  const marcadores: MarcadorEstacion[] = useMemo(
    () =>
      estaciones
        .filter((e) => e[st.fuel] != null)
        .map((e) => ({
          numero: e.numero,
          nombre: e.nombre,
          lat: e.latitud as number,
          lng: e.longitud as number,
          precio: e[st.fuel] as number,
          categoria: categorizar(e[st.fuel] as number, preciosFuel),
        })),
    [estaciones, st.fuel, preciosFuel],
  );

  const disponibles = useMemo(() => {
    const s = new Set<TipoCombustible>();
    for (const f of FUELS) {
      if (estaciones.some((e) => e[f] != null)) s.add(f);
    }
    return s;
  }, [estaciones]);

  const kpis = useMemo(() => {
    if (preciosFuel.length === 0) return null;
    const suma = preciosFuel.reduce((a, b) => a + b, 0);
    return {
      prom: suma / preciosFuel.length,
      min: Math.min(...preciosFuel),
      max: Math.max(...preciosFuel),
      count: preciosFuel.length,
    };
  }, [preciosFuel]);

  const ranking: FilaRanking[] = useMemo(
    () =>
      [...marcadores]
        .sort((a, b) => a.precio - b.precio)
        .slice(0, 10)
        .map((m) => ({
          id: m.numero,
          nombre: m.nombre.length > 26 ? m.nombre.slice(0, 24) + "…" : m.nombre,
          precio: m.precio,
          categoria: m.categoria,
        })),
    [marcadores],
  );

  const buscarEstacion = (numero: string | null): EstacionGasolina | null =>
    numero ? (estaciones.find((e) => e.numero === numero) ?? null) : null;

  const seleccionada = buscarEstacion(st.seleccionadoNumero);
  const seleccionadaCat: Categoria | null =
    seleccionada && seleccionada[st.fuel] != null
      ? categorizar(seleccionada[st.fuel] as number, preciosFuel)
      : null;

  // Calculadora: base (fijada o más barata) vs referencia (seleccionada o más cara).
  const calc = useMemo(() => {
    if (marcadores.length === 0) return null;
    const ordenadas = [...marcadores].sort((a, b) => a.precio - b.precio);
    const barata = ordenadas[0];
    const cara = ordenadas[ordenadas.length - 1];

    const baseM =
      (st.baseNumero && marcadores.find((m) => m.numero === st.baseNumero)) || barata;
    const refM =
      (st.seleccionadoNumero &&
        marcadores.find((m) => m.numero === st.seleccionadoNumero)) ||
      cara;

    const mismaBaseRef = refM.numero === baseM.numero;
    return {
      baseNombre: baseM.nombre,
      basePrecio: baseM.precio,
      esBase: !!st.baseNumero,
      refNombre: mismaBaseRef ? null : refM.nombre,
      refPrecio: mismaBaseRef ? null : refM.precio,
      refEsSeleccion: !!st.seleccionadoNumero,
    };
  }, [marcadores, st.baseNumero, st.seleccionadoNumero]);

  const cercanas: Cercana[] = useMemo(() => {
    if (!st.punto) return [];
    const lista = marcadores
      .map((m) => ({
        numero: m.numero,
        nombre: m.nombre,
        precio: m.precio,
        categoria: m.categoria,
        dist: distKm(st.punto!.lat, st.punto!.lng, m.lat, m.lng),
      }))
      .sort((a, b) => a.dist - b.dist);
    const dentro = lista.filter((x) => x.dist <= 2);
    return dentro.length >= 2 ? dentro.slice(0, 8) : lista.slice(0, 5);
  }, [marcadores, st.punto]);

  const cercanasDentro = cercanas.filter((c) => c.dist <= 2).length;
  const hayCercanas = !!st.punto && cercanas.length > 0;
  const distanciaSeleccion =
    st.punto && seleccionada?.latitud != null && seleccionada?.longitud != null
      ? distKm(st.punto.lat, st.punto.lng, seleccionada.latitud, seleccionada.longitud)
      : null;

  // ── Handlers ───────────────────────────────────────────
  function elegirEstado(o: Opcion) {
    setParams({ estado: o.value });
  }
  function elegirMunicipio(o: Opcion) {
    setParams({ estado: estadoSel, municipio: o.value });
  }

  const sinUbicacion = !estadoSel || !munSel;
  const noEncontrado =
    query.error instanceof ApiError &&
    (query.error.status === 404 || query.error.status === 400);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-3xl md:text-4xl">Gasolina</h1>
      <p className="mt-1 text-ink-700">
        Elige tu estado y municipio para comparar precios por estación.
      </p>

      {/* Selectores en cascada */}
      <div className="mt-5 grid gap-3 sm:grid-cols-2 md:max-w-xl">
        <AutocompleteInput
          label="Estado"
          placeholder="Escribe tu estado"
          opciones={opcionesEstado}
          valorTexto={estadoSel ? capitalizar(estadoSel) : ""}
          onSelect={elegirEstado}
        />
        <AutocompleteInput
          label="Municipio"
          placeholder={estadoSel ? "Escribe tu municipio" : "Elige un estado primero"}
          opciones={opcionesMunicipio}
          valorTexto={munSel ? capitalizar(munSel) : ""}
          onSelect={elegirMunicipio}
          disabled={!estadoSel}
        />
      </div>

      <div className="mt-8">
        {sinUbicacion ? (
          <WelcomeState
            titulo="Elige una ubicación"
            detalle="Selecciona tu estado y municipio para ver las gasolineras y sus precios."
          />
        ) : query.isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-64" />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20" />
              ))}
            </div>
            <Skeleton className="h-96" />
          </div>
        ) : noEncontrado ? (
          <ComingSoonState
            titulo="Aún no tenemos datos aquí"
            detalle={`De momento no hay precios de gasolina para ${capitalizar(munSel)}, ${capitalizar(estadoSel)}.`}
          />
        ) : query.isError ? (
          <ErrorState
            titulo="No se pudieron cargar los precios"
            detalle="La fuente puede estar temporalmente fuera de servicio. Intenta de nuevo."
            accion={
              <button
                onClick={() => query.refetch()}
                className="rounded-full bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Reintentar
              </button>
            }
          />
        ) : (
          query.data && (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <FuelPills
                  fuel={st.fuel}
                  disponibles={disponibles}
                  onChange={(f) => dispatch({ type: "SET_FUEL", fuel: f })}
                />
                <FreshnessBadge fuente={query.data.fuente} fecha={query.data.fecha_datos} />
              </div>

              <KpiRow
                items={[
                  { label: "Promedio", valor: kpis ? formatearPesos(kpis.prom) : "—" },
                  { label: "Mínimo", valor: kpis ? formatearPesos(kpis.min) : "—", tono: "low" },
                  { label: "Máximo", valor: kpis ? formatearPesos(kpis.max) : "—", tono: "high" },
                  { label: "Estaciones", valor: kpis ? String(kpis.count) : "0" },
                ]}
              />

              {/*
                Dashboard de 3 paneles en pantallas anchas:
                ranking (izq) · mapa (centro, el más grande) · calculadora+detalle (der).
                Colapsa a 2 columnas en tablet y a 1 en móvil (el mapa va primero).
              */}
              <div className="grid gap-5 lg:grid-cols-12">
                {/* Ranking (+ cercanas al fijar punto) — izquierda en desktop,
                    debajo del mapa en móvil. Al fijar punto, el Top 10 se compacta
                    (menos filas, scroll interno) para dejar sitio a las cercanas.
                    content-start evita que las cards se estiren cuando la columna
                    crece; en pantalla partida (md) se ponen lado a lado. */}
                <div
                  className={[
                    "order-2 grid content-start gap-5 lg:order-1 lg:col-span-5 lg:grid-cols-1 xl:col-span-3",
                    hayCercanas ? "md:grid-cols-2" : "",
                  ].join(" ")}
                >
                  <RankingTable
                    titulo={`Top 10 más baratas · ${capitalizar(st.fuel)}`}
                    filas={ranking}
                    seleccionadoId={st.seleccionadoNumero}
                    onSelect={(id) => dispatch({ type: "SELECT", numero: id })}
                    mostrarCategoria={false}
                    compacto={hayCercanas}
                  />
                  {hayCercanas && (
                    <NearbyList
                      titulo={
                        cercanasDentro >= 2
                          ? `${cercanasDentro} gasolineras en 2 km`
                          : "Más cercanas a ti"
                      }
                      items={cercanas}
                      seleccionadoId={st.seleccionadoNumero}
                      onSelect={(n) => dispatch({ type: "SELECT", numero: n })}
                    />
                  )}
                </div>

                {/* Mapa — centro, el panel más grande */}
                <div className="order-1 flex flex-col gap-3 lg:order-2 lg:col-span-7 xl:col-span-6">
                  <MapToolbar
                    filtroCategoria={st.filtroCategoria}
                    onToggleFiltro={(c) => dispatch({ type: "TOGGLE_FILTRO", categoria: c })}
                    modoFijar={st.modoFijar}
                    tienePunto={!!st.punto}
                    onToggleFijar={() => dispatch({ type: "TOGGLE_MODO_FIJAR" })}
                    onUbicarme={(lat, lng, manual) =>
                      dispatch({ type: "SET_PUNTO", punto: { lat, lng, manual } })
                    }
                    onQuitarPunto={() => dispatch({ type: "CLEAR_PUNTO" })}
                  />
                  {/* flex-1 hace que el mapa llene la columna; como el grid estira
                      todas las columnas a la más alta, el mapa iguala la altura de
                      las cartas laterales. min-h evita que se aplaste en móvil. */}
                  <div className="min-h-[420px] flex-1">
                    <Suspense fallback={<Skeleton className="size-full" />}>
                      <StationMap
                        estaciones={marcadores}
                        seleccionadoNumero={st.seleccionadoNumero}
                        filtroCategoria={st.filtroCategoria}
                        punto={st.punto}
                        modoFijar={st.modoFijar}
                        onSelect={onSelectEstacion}
                        onDeselect={onDeselectEstacion}
                        onFijarPunto={onFijarPunto}
                      />
                    </Suspense>
                  </div>
                </div>

                {/* Rail derecho — calculadora + detalle.
                    En tablet ocupa el ancho completo con 2 columnas internas. */}
                <div className="order-3 grid content-start gap-5 sm:grid-cols-2 lg:col-span-12 xl:col-span-3 xl:grid-cols-1">
                  {calc && (
                    <FuelCalculator
                      tipo={st.calc.tipo}
                      monto={st.calc.monto}
                      onTipo={(t) => dispatch({ type: "SET_CALC_TIPO", tipo: t })}
                      onMonto={(n) => dispatch({ type: "SET_CALC_MONTO", monto: n })}
                      baseNombre={calc.baseNombre}
                      basePrecio={calc.basePrecio}
                      esBase={calc.esBase}
                      onResetBase={() => dispatch({ type: "RESET_BASE" })}
                      refNombre={calc.refNombre}
                      refPrecio={calc.refPrecio}
                      refEsSeleccion={calc.refEsSeleccion}
                    />
                  )}
                  <StationDetail
                    estacion={seleccionada}
                    categoria={seleccionadaCat}
                    fuel={st.fuel}
                    distanciaKm={distanciaSeleccion}
                    esBase={!!st.seleccionadoNumero && st.baseNumero === st.seleccionadoNumero}
                    onFijarBase={() =>
                      st.seleccionadoNumero &&
                      dispatch({ type: "SET_BASE", numero: st.seleccionadoNumero })
                    }
                  />
                </div>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
