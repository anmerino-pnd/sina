import { COLOR_CATEGORIA, type Categoria } from "@/lib/precios";

const ESTILO: Record<Categoria, string> = {
  Barato: "bg-price-low/12 text-price-low",
  Promedio: "bg-price-mid/15 text-price-mid",
  Caro: "bg-price-high/12 text-price-high",
};

export function CategoryBadge({ categoria }: { categoria: Categoria }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold ${ESTILO[categoria]}`}
    >
      <span
        className="inline-block size-1.5 rounded-full"
        style={{ background: COLOR_CATEGORIA[categoria] }}
        aria-hidden="true"
      />
      {categoria}
    </span>
  );
}
