// Lógica de categorización de precios, idéntica a la de los dashboards actuales:
// se parte el rango [min, max] en tercios → Barato / Promedio / Caro.

export type Categoria = "Barato" | "Promedio" | "Caro";

export function categorizar(precio: number, todos: number[]): Categoria {
  const v = todos.filter((p) => p != null && !Number.isNaN(p));
  if (!v.length) return "Promedio";
  const mn = Math.min(...v);
  const mx = Math.max(...v);
  const r = mx - mn;
  if (r === 0) return "Promedio";
  if (precio <= mn + r / 3) return "Barato";
  if (precio <= mn + (2 * r) / 3) return "Promedio";
  return "Caro";
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
