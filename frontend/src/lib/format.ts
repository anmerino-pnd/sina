const mxn = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  minimumFractionDigits: 2,
});

const fechaLarga = new Intl.DateTimeFormat("es-MX", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

export function formatearPesos(valor: number | null | undefined): string {
  if (valor == null || Number.isNaN(valor)) return "—";
  return mxn.format(valor);
}

export function formatearFecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return fechaLarga.format(d);
}

/** Convierte "hermosillo" → "Hermosillo", "gas lp" → "Gas Lp". */
export function capitalizar(texto: string): string {
  return texto.replace(/\b\p{L}/gu, (c) => c.toUpperCase());
}
