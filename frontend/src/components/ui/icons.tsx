/** Íconos de línea, minimalistas. Sin emojis: tono elegante y formal. */
interface IconProps {
  className?: string;
}

const base = "size-[1.1em]";

export function IconPin({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`${base} ${className}`} aria-hidden="true">
      <path
        d="M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="10" r="2.4" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export function IconTarget({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`${base} ${className}`} aria-hidden="true">
      <circle cx="12" cy="12" r="7.5" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="2.2" fill="currentColor" />
      <path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function IconCheck({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`${base} ${className}`} aria-hidden="true">
      <path d="M5 12.5 10 17.5 19 6.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconRoute({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`${base} ${className}`} aria-hidden="true">
      <path d="M6 3 3 6l3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 6h9a4 4 0 0 1 4 4v0a4 4 0 0 1-4 4H8a4 4 0 0 0-4 4v1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="19" cy="19" r="2.4" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export function IconSun({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`${base} ${className}`} aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8 6 18M18 6l1.8-1.8"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function IconMoon({ className = "" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`${base} ${className}`} aria-hidden="true">
      <path
        d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z"
        fill="currentColor"
        opacity="0.15"
      />
      <path
        d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}
