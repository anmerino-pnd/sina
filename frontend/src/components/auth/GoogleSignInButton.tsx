import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";

/**
 * Renderiza el botón oficial de Google Identity Services.
 * Si no hay client_id configurado en el backend, no se muestra (feature flag).
 */
export function GoogleSignInButton() {
  const { clientId, loadGis, signInWithCredential } = useAuth();
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clientId || !containerRef.current) return;
    let cancelled = false;

    loadGis()
      .then(() => {
        if (cancelled || !containerRef.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          cancel_on_tap_outside: true,
          callback: (resp) => {
            signInWithCredential(resp.credential).catch(() =>
              setError("No se pudo iniciar sesión. Intenta de nuevo."),
            );
          },
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "pill",
          locale: "es-MX",
        });
      })
      .catch(() => setError("No se pudo cargar Google Sign-In."));

    return () => {
      cancelled = true;
    };
  }, [clientId, loadGis, signInWithCredential]);

  if (!clientId) return null;

  return (
    <div className="flex flex-col items-end gap-1">
      <div ref={containerRef} className="min-h-10" />
      {error && <p className="text-xs text-price-high">{error}</p>}
    </div>
  );
}
