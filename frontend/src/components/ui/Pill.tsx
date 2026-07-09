interface PillProps {
  activo: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

export function Pill({ activo, disabled, onClick, children }: PillProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      aria-pressed={activo}
      onClick={onClick}
      className={[
        "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-40",
        activo
          ? "bg-brand-600 text-white"
          : "border border-sand-300 bg-surface text-ink-700 hover:bg-sand-100",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

export function PillGroup({
  label,
  children,
}: {
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {label && (
        <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          {label}
        </span>
      )}
      {children}
    </div>
  );
}
