// Contratos JSON del backend SINA. Fuente de verdad para el tipado del cliente.

export type Fuente = "cache" | "api" | "cache_vencido";

export interface CatalogoResponse {
  // { estado_nombre: [municipio_nombre, ...] } — todo en minúsculas.
  estados: Record<string, string[]>;
}

export interface HealthDominio {
  ultima_actualizacion: string | null;
  vigente: boolean | null;
}

export interface HealthResponse {
  status: string;
  gasolina: HealthDominio;
  gas_lp: HealthDominio;
  supermercados: HealthDominio;
}

// ── Gasolina ────────────────────────────────────────────
export interface EstacionGasolina {
  numero: string;
  nombre: string;
  direccion: string;
  magna: number | null;
  premium: number | null;
  diesel: number | null;
  latitud: number | null;
  longitud: number | null;
  fecha_extraccion: string;
}

export interface GasolinaResponse {
  status: string;
  fuente: Fuente;
  fecha_datos: string | null;
  estado: string;
  municipio: string;
  total: number;
  datos: EstacionGasolina[];
}

export type TipoCombustible = "magna" | "premium" | "diesel";

// ── Gas LP ──────────────────────────────────────────────
export interface Localidad {
  id: number;
  nombre: string;
}

export interface LocalidadesResponse {
  estado: string;
  municipio: string;
  entidad_id: number;
  municipio_id: string;
  localidades: Localidad[];
}

export interface GasLPItem {
  numero_permiso: string;
  marca_comercial: string | null;
  tipo: "autotanque" | "recipiente";
  capacidad_recipiente: number | null;
  precio: number;
  entidad_nombre: string;
  municipio_nombre: string;
  localidad_nombre: string;
  fecha_extraccion: string;
  vigente: boolean;
}

export interface GasLPResponse {
  localidad: string;
  municipio: string;
  estado: string;
  autotanques: GasLPItem[];
  recipientes: GasLPItem[];
  fuente: Fuente;
  fecha_datos: string | null;
  total: number;
}

// ── Supermercados ───────────────────────────────────────
export interface Producto {
  pid: number;
  producto: string;
  precio: number;
  tienda: string;
  departamento: string | null;
  categoria: string | null;
  subcategoria: string | null;
  fecha_actualizacion: string;
}

export interface SupermercadosResponse {
  status: string;
  q: string | null;
  total: number;
  datos: Producto[];
}

// ── Auth ────────────────────────────────────────────────
export interface Usuario {
  // Identidad estable de Google (sub). Nunca es el email.
  user_id: string;
  username: string | null;
  nombre: string | null;
  foto_url: string | null;
  needs_username: boolean;
}
