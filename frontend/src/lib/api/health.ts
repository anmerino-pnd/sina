import { apiFetch } from "@/lib/api/client";
import type { HealthResponse } from "@/lib/types";

export function obtenerHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
