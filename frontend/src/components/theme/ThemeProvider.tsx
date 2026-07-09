import { createContext, useCallback, useContext, useMemo, useState } from "react";

import {
  aplicarTema,
  guardarTema,
  temaInicial,
  type Tema,
} from "@/lib/theme";
import { IconMoon, IconSun } from "@/components/ui/icons";

interface ThemeContextValue {
  tema: Tema;
  alternar: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [tema, setTema] = useState<Tema>(() => temaInicial());

  const alternar = useCallback(() => {
    setTema((prev) => {
      const next: Tema = prev === "dark" ? "light" : "dark";
      aplicarTema(next);
      guardarTema(next);
      return next;
    });
  }, []);

  const value = useMemo(() => ({ tema, alternar }), [tema, alternar]);
  return <ThemeContext value={value}>{children}</ThemeContext>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme debe usarse dentro de <ThemeProvider>");
  return ctx;
}

export function ThemeToggle() {
  const { tema, alternar } = useTheme();
  const esOscuro = tema === "dark";
  return (
    <button
      onClick={alternar}
      aria-label={esOscuro ? "Activar modo claro" : "Activar modo oscuro"}
      title={esOscuro ? "Modo claro" : "Modo oscuro"}
      className="grid size-9 place-items-center rounded-full border border-sand-300 bg-surface text-ink-700 hover:bg-sand-100"
    >
      {esOscuro ? <IconMoon className="size-5" /> : <IconSun className="size-5" />}
    </button>
  );
}
