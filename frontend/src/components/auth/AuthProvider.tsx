import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type { Usuario } from "@/lib/types";
import {
  autenticarConGoogle,
  cerrarSesion,
  obtenerUsuarioActual,
} from "@/lib/api/auth";
import { obtenerConfig } from "@/lib/api/config";

const GIS_SRC = "https://accounts.google.com/gsi/client";

interface AuthContextValue {
  user: Usuario | null;
  status: "loading" | "ready";
  /** null → login deshabilitado (sin client_id configurado en el backend). */
  clientId: string | null;
  setUser: (u: Usuario | null) => void;
  signInWithCredential: (credential: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Garantiza que el script de Google Identity Services esté cargado. */
  loadGis: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

let gisPromise: Promise<void> | null = null;
function ensureGisScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (gisPromise) return gisPromise;
  gisPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("No se pudo cargar Google Sign-In"));
    document.head.appendChild(script);
  });
  return gisPromise;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    (async () => {
      // config y sesión en paralelo; ninguno debe tumbar el arranque.
      const [cfg, actual] = await Promise.allSettled([
        obtenerConfig(),
        obtenerUsuarioActual(),
      ]);
      if (!mounted.current) return;
      if (cfg.status === "fulfilled") {
        setClientId(cfg.value.google_client_id || null);
      }
      if (actual.status === "fulfilled") setUser(actual.value);
      setStatus("ready");
    })();
    return () => {
      mounted.current = false;
    };
  }, []);

  const signInWithCredential = useCallback(async (credential: string) => {
    const u = await autenticarConGoogle(credential);
    setUser(u);
  }, []);

  const signOut = useCallback(async () => {
    await cerrarSesion();
    window.google?.accounts.id.disableAutoSelect();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      clientId,
      setUser,
      signInWithCredential,
      signOut,
      loadGis: ensureGisScript,
    }),
    [user, status, clientId, signInWithCredential, signOut],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
