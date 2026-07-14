import { memo, useEffect, useRef } from "react";
import L from "leaflet";
import {
  Circle,
  CircleMarker,
  MapContainer,
  Marker,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

import { COLOR_CATEGORIA, type Categoria } from "@/lib/precios";
import { formatearPesos } from "@/lib/format";
import { useTheme } from "@/components/theme/ThemeProvider";
import type { PuntoUsuario } from "@/features/gasolina/useGasolinaState";

export interface MarcadorEstacion {
  numero: string;
  nombre: string;
  lat: number;
  lng: number;
  precio: number;
  categoria: Categoria;
}

interface Props {
  estaciones: MarcadorEstacion[];
  seleccionadoNumero: string | null;
  filtroCategoria: Categoria | null;
  punto: PuntoUsuario | null;
  modoFijar: boolean;
  onSelect: (numero: string) => void;
  onDeselect: () => void;
  onFijarPunto: (lat: number, lng: number) => void;
}

const CENTRO_MX: [number, number] = [23.6345, -102.5528];

// Los iconos solo dependen de (color, seleccionado): pocas combinaciones, así
// que se cachean para no crear un L.divIcon por marcador en cada render.
const _iconos = new Map<string, L.DivIcon>();

function iconoPunto(color: string, seleccionado: boolean): L.DivIcon {
  const clave = `${color}|${seleccionado}`;
  const cacheado = _iconos.get(clave);
  if (cacheado) return cacheado;

  const sz = seleccionado ? 30 : 15;
  const bw = seleccionado ? 3 : 2;
  const sh = seleccionado
    ? `0 0 0 5px ${color}35, 0 2px 8px rgba(0,0,0,0.28)`
    : "0 1px 3px rgba(0,0,0,0.22)";
  const icono = L.divIcon({
    html: `<div style="width:${sz}px;height:${sz}px;background:${color};border-radius:50%;border:${bw}px solid white;box-shadow:${sh}"></div>`,
    className: "",
    iconSize: [sz, sz],
    iconAnchor: [sz / 2, sz / 2],
  });
  _iconos.set(clave, icono);
  return icono;
}

/**
 * Marcador individual memoizado: al cambiar la selección o el filtro solo
 * re-renderizan los marcadores cuyas props cambiaron, no todo el municipio.
 * Requiere que `onSelect` sea estable (useCallback en la página).
 */
const MarcadorPunto = memo(function MarcadorPunto({
  estacion: e,
  sel,
  activo,
  onSelect,
}: {
  estacion: MarcadorEstacion;
  sel: boolean;
  activo: boolean;
  onSelect: (numero: string) => void;
}) {
  return (
    <Marker
      position={[e.lat, e.lng]}
      icon={iconoPunto(COLOR_CATEGORIA[e.categoria], sel)}
      opacity={activo ? 1 : 0.18}
      interactive={activo}
      zIndexOffset={sel ? 999 : 0}
      eventHandlers={{ click: () => onSelect(e.numero) }}
    >
      <Tooltip direction="top" offset={[0, -8]}>
        <strong>{e.nombre}</strong>
        <br />
        {formatearPesos(e.precio)} · {e.categoria}
      </Tooltip>
    </Marker>
  );
});

/**
 * Corrige el tamaño del mapa. Leaflet cachea las dimensiones del contenedor al
 * inicializar; como el mapa monta perezoso (lazy/Suspense) durante el reflow del
 * grid, a veces mide una altura equivocada y pinta tiles en gris hasta un resize
 * (el clásico "hay que dar F5"). Invalidamos tras el layout y en cada resize.
 */
function InvalidarTamano() {
  const map = useMap();
  useEffect(() => {
    const fix = () => map.invalidateSize();
    requestAnimationFrame(fix); // tras revelar el Suspense / asentar el layout
    const ro = new ResizeObserver(fix); // cubre breakpoints md/xl + crecimiento flex-1
    ro.observe(map.getContainer());
    return () => ro.disconnect();
  }, [map]);
  return null;
}

/** Ajusta el encuadre cuando cambia el conjunto de estaciones. */
function AjustarEncuadre({ estaciones }: { estaciones: MarcadorEstacion[] }) {
  const map = useMap();
  const clave = estaciones.map((e) => e.numero).join(",");
  useEffect(() => {
    if (estaciones.length === 0) return;
    const bounds = L.latLngBounds(estaciones.map((e) => [e.lat, e.lng]));
    map.fitBounds(bounds, { padding: [28, 28] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave]);
  return null;
}

/** Centra la vista en la estación seleccionada. */
function CentrarSeleccion({
  estaciones,
  seleccionadoNumero,
}: {
  estaciones: MarcadorEstacion[];
  seleccionadoNumero: string | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (!seleccionadoNumero) return;
    const e = estaciones.find((x) => x.numero === seleccionadoNumero);
    if (e) map.setView([e.lat, e.lng], 15, { animate: true, duration: 0.5 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seleccionadoNumero]);
  return null;
}

/** Escucha clics en el mapa: fijar punto o deseleccionar. */
function ClicMapa({
  modoFijar,
  onFijarPunto,
  onDeselect,
}: {
  modoFijar: boolean;
  onFijarPunto: (lat: number, lng: number) => void;
  onDeselect: () => void;
}) {
  useMapEvents({
    click(e) {
      if (modoFijar) onFijarPunto(e.latlng.lat, e.latlng.lng);
      else onDeselect();
    },
  });
  return null;
}

export default function StationMap({
  estaciones,
  seleccionadoNumero,
  filtroCategoria,
  punto,
  modoFijar,
  onSelect,
  onDeselect,
  onFijarPunto,
}: Props) {
  const contenedorRef = useRef<HTMLDivElement>(null);
  const { tema } = useTheme();
  const tileUrl =
    tema === "dark"
      ? "https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
      : "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";

  useEffect(() => {
    if (modoFijar) contenedorRef.current?.classList.add("cursor-crosshair");
    else contenedorRef.current?.classList.remove("cursor-crosshair");
  }, [modoFijar]);

  return (
    <div
      ref={contenedorRef}
      className="isolate size-full overflow-hidden rounded-[var(--radius-card)] border border-sand-200"
    >
      <MapContainer
        center={CENTRO_MX}
        zoom={5}
        className="size-full"
        zoomControl
      >
        <TileLayer
          key={tema}
          url={tileUrl}
          attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />

        <InvalidarTamano />
        <AjustarEncuadre estaciones={estaciones} />
        <CentrarSeleccion estaciones={estaciones} seleccionadoNumero={seleccionadoNumero} />
        <ClicMapa modoFijar={modoFijar} onFijarPunto={onFijarPunto} onDeselect={onDeselect} />

        {estaciones.map((e) => (
          <MarcadorPunto
            key={e.numero}
            estacion={e}
            sel={e.numero === seleccionadoNumero}
            activo={filtroCategoria === null || e.categoria === filtroCategoria}
            onSelect={onSelect}
          />
        ))}

        {punto && (
          <>
            <CircleMarker
              center={[punto.lat, punto.lng]}
              radius={8}
              pathOptions={{
                color: "white",
                weight: 3,
                fillColor: punto.manual ? "#241f1b" : "#0071e3",
                fillOpacity: 1,
              }}
            >
              <Tooltip permanent direction="top">
                {punto.manual ? "Tu punto de referencia" : "Tu ubicación"}
              </Tooltip>
            </CircleMarker>
            {punto.manual && (
              <Circle
                center={[punto.lat, punto.lng]}
                radius={2000}
                pathOptions={{
                  color: "#241f1b",
                  weight: 1.5,
                  dashArray: "6 4",
                  fillColor: "#241f1b",
                  fillOpacity: 0.04,
                }}
              />
            )}
          </>
        )}
      </MapContainer>
    </div>
  );
}
