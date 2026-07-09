import { Pill, PillGroup } from "@/components/ui/Pill";
import type { TipoCombustible } from "@/lib/types";

const TIPOS: { key: TipoCombustible; label: string }[] = [
  { key: "magna", label: "Magna" },
  { key: "premium", label: "Premium" },
  { key: "diesel", label: "Diésel" },
];

interface Props {
  fuel: TipoCombustible;
  disponibles: Set<TipoCombustible>;
  onChange: (fuel: TipoCombustible) => void;
}

export function FuelPills({ fuel, disponibles, onChange }: Props) {
  return (
    <PillGroup label="Combustible">
      {TIPOS.map((t) => (
        <Pill
          key={t.key}
          activo={fuel === t.key}
          disabled={!disponibles.has(t.key)}
          onClick={() => onChange(t.key)}
        >
          {t.label}
        </Pill>
      ))}
    </PillGroup>
  );
}
