// Categorización de precios por DESVIACIÓN respecto al precio típico, robusta a
// outliers. En vez de partir el rango [min, max] (que dos estaciones atípicas
// distorsionan), se ancla en la MEDIANA y se mide qué tan lejos está cada precio
// usando la dispersión robusta (MAD → sigma robusta). Coherente: mismo precio ⇒
// mismo color siempre; y honesto: si el mercado es parejo, casi todo sale
// "Promedio" y solo destacan las estaciones realmente baratas (o caras).
//
//   z = (precio − mediana) / escala      escala = max(1.4826·MAD, PISO_REL·mediana)
//   z ≤ −K → Barato    z ≥ +K → Caro    resto → Promedio

export type Categoria = "Barato" | "Promedio" | "Caro";

/** Mínimo de precios para juzgar; por debajo, todo "Promedio" (datos insuficientes). */
const N_MIN = 4;
/**
 * Umbral en unidades de sigma robusta: qué tan lejos de lo típico cuenta como
 * Barato/Caro. 0.6745 equivale al rango intercuartílico de una normal (± ese
 * valor cubre el 50% central), así que "más allá" = notablemente barato/caro.
 * Afinado con datos reales de Hermosillo (magna/premium/diésel) para dar un
 * reparto sano de colores sin forzar tercios.
 */
const K_UMBRAL = 0.6745;
/** Piso de dispersión (fracción de la mediana): evita bandas que colapsan si MAD ≈ 0. */
const PISO_REL = 0.008;
/** Factor de consistencia normal para convertir MAD en desviación estándar robusta. */
const MAD_A_SIGMA = 1.4826;

function mediana(ordenados: number[]): number {
  const n = ordenados.length;
  const m = n >> 1;
  return n % 2 ? ordenados[m] : (ordenados[m - 1] + ordenados[m]) / 2;
}

interface EscalaRobusta {
  med: number;
  escala: number;
  n: number;
}

// Memoiza por referencia del arreglo: los llamadores pasan un `todos` memoizado
// (p. ej. `preciosFuel`), así que las ~N llamadas por render comparten un solo
// cálculo de mediana/MAD (evita recomputar O(n log n) por cada estación).
const _cache = new WeakMap<number[], EscalaRobusta>();

function estadisticasRobustas(todos: number[]): EscalaRobusta {
  const cacheado = _cache.get(todos);
  if (cacheado) return cacheado;

  const v = todos.filter((p) => p != null && !Number.isNaN(p)).sort((a, b) => a - b);
  let stats: EscalaRobusta;
  if (v.length < N_MIN) {
    stats = { med: v.length ? mediana(v) : 0, escala: 0, n: v.length };
  } else {
    const med = mediana(v);
    const desv = v.map((x) => Math.abs(x - med)).sort((a, b) => a - b);
    const mad = mediana(desv);
    const escala = Math.max(MAD_A_SIGMA * mad, PISO_REL * med);
    stats = { med, escala, n: v.length };
  }
  _cache.set(todos, stats);
  return stats;
}

export function categorizar(precio: number, todos: number[]): Categoria {
  const { med, escala, n } = estadisticasRobustas(todos);
  if (n < N_MIN || escala <= 0) return "Promedio";
  const z = (precio - med) / escala;
  if (z <= -K_UMBRAL) return "Barato";
  if (z >= K_UMBRAL) return "Caro";
  return "Promedio";
}

// Tokens de color semánticos (definidos en styles/index.css).
export const COLOR_CATEGORIA: Record<Categoria, string> = {
  Barato: "var(--color-price-low)",
  Promedio: "var(--color-price-mid)",
  Caro: "var(--color-price-high)",
};

// Clases utilitarias para texto de precio según categoría.
export const CLASE_PRECIO: Record<Categoria, string> = {
  Barato: "text-price-low",
  Promedio: "text-price-mid",
  Caro: "text-price-high",
};
