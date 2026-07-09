import { apiFetch } from "@/lib/api/client";

export interface ClientConfig {
  // Client ID público de Google OAuth. "" → login deshabilitado (feature flag).
  google_client_id: string;
}

export function obtenerConfig(): Promise<ClientConfig> {
  return apiFetch<ClientConfig>("/config");
}
