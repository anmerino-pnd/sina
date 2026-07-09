interface EstadoProps {
  titulo: string;
  detalle?: string;
  accion?: React.ReactNode;
}

function Contenedor({ titulo, detalle, accion }: EstadoProps) {
  return (
    <div className="rounded-[var(--radius-card)] border border-dashed border-sand-300 bg-surface/60 px-6 py-16 text-center">
      <span className="mx-auto block h-px w-10 bg-sand-300" aria-hidden="true" />
      <h3 className="mt-5 text-lg text-ink-900">{titulo}</h3>
      {detalle && <p className="mx-auto mt-1 max-w-md text-sm text-ink-500">{detalle}</p>}
      {accion && <div className="mt-5">{accion}</div>}
    </div>
  );
}

/** Bienvenida: aún no se ha elegido ubicación. */
export function WelcomeState(props: EstadoProps) {
  return <Contenedor {...props} />;
}

/** Sin datos para la ubicación (404 o total 0). */
export function ComingSoonState(props: EstadoProps) {
  return <Contenedor {...props} />;
}

/** Error recuperable. */
export function ErrorState(props: EstadoProps) {
  return <Contenedor {...props} />;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-sand-200 ${className}`} />;
}
