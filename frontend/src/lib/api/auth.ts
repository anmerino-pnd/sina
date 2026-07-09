import { apiFetch } from "@/lib/api/client";
import type { Usuario } from "@/lib/types";

/** Envía el ID token de Google; el backend lo verifica y abre sesión (cookie). */
export function autenticarConGoogle(credential: string): Promise<Usuario> {
  return apiFetch<Usuario>("/auth/google", {
    method: "POST",
    body: { credential },
  });
}

export function cerrarSesion(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}

/** Devuelve el usuario actual o null (401) si no hay sesión. */
export async function obtenerUsuarioActual(): Promise<Usuario | null> {
  try {
    return await apiFetch<Usuario>("/me");
  } catch (e) {
    if (typeof e === "object" && e && "status" in e && e.status === 401) {
      return null;
    }
    throw e;
  }
}

export function fijarUsername(username: string): Promise<Usuario> {
  return apiFetch<Usuario>("/me", { method: "PATCH", body: { username } });
}
