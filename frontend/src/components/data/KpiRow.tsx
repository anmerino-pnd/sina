interface Kpi {
  label: string;
  valor: string;
  tono?: "low" | "high" | "neutral";
}

const TONO: Record<NonNullable<Kpi["tono"]>, string> = {
  low: "text-price-low",
  high: "text-price-high",
  neutral: "text-ink-900",
};

export function KpiRow({ items }: { items: Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {items.map((k) => (
        <div
          key={k.label}
          className="rounded-[var(--radius-card)] border border-sand-200 bg-surface p-4 shadow-[var(--shadow-card)]"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
            {k.label}
          </p>
          <p className={`tabular mt-1 text-2xl font-semibold ${TONO[k.tono ?? "neutral"]}`}>
            {k.valor}
          </p>
        </div>
      ))}
    </div>
  );
}
