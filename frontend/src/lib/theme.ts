export type Tema = "light" | "dark";

const KEY = "sina.theme";

export function temaGuardado(): Tema | null {
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" ? v : null;
}

export function temaInicial(): Tema {
  return (
    temaGuardado() ??
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );
}

export function aplicarTema(t: Tema): void {
  document.documentElement.classList.toggle("dark", t === "dark");
}

export function guardarTema(t: Tema): void {
  localStorage.setItem(KEY, t);
}
