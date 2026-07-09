/**
 * Marca de Sina — colibrí de Costa estilizado.
 * La gorguera (garganta) lleva el violeta-magenta iridiscente del ave;
 * el cuerpo usa el verde-bronce del dorso. Mark ilustrada real, no un blob.
 */
export function SinaMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      role="img"
      aria-label="Sina"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* ala trasera */}
      <path
        d="M22 20c-6-5-14-6-19-2 3 6 10 9 17 8"
        fill="var(--color-sage-400)"
        opacity="0.55"
      />
      {/* cuerpo */}
      <path
        d="M20 18c4-1 8 0 11 3 4 4 9 5 13 3-1 4-5 7-10 7-3 3-8 4-12 2-3-1-5-4-5-8 0-4 1-7 3-10z"
        fill="var(--color-sage-500)"
      />
      {/* gorguera iridiscente */}
      <path
        d="M17 25c2 2 5 3 8 2-1 3-4 5-7 4-2-1-3-4-1-6z"
        fill="var(--color-brand-600)"
      />
      <path
        d="M18 26c1.6 1.3 3.6 1.9 5.6 1.4-.8 1.9-2.7 3-4.6 2.4"
        fill="var(--color-flare-500)"
      />
      {/* pico */}
      <path
        d="M6 30l11-3-1 3z"
        fill="var(--color-ink-700)"
      />
      {/* ojo */}
      <circle cx="27" cy="20.5" r="1.4" fill="var(--color-ink-900)" />
    </svg>
  );
}
