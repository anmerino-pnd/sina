// Cliente HTTP mínimo. Mismo origen que el backend → cookies de sesión viajan
// solas (credentials: "include" por si en dev el proxy cambia de origen).
// El token CSRF (double-submit) se lee de la cookie no-httpOnly y se reenvía
// en el header X-CSRF-Token para cualquier método mutante.

const CSRF_COOKIE = "sina_csrf";
const CSRF_HEADER = "X-CSRF-Token";

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function leerCookie(nombre: string): string | null {
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + nombre + "=([^;]*)"),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

interface RequestOpts {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

export async function apiFetch<T>(
  path: string,
  { method = "GET", body, signal }: RequestOpts = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const esMutante = method !== "GET" && method !== "HEAD";

  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (esMutante) {
    const csrf = leerCookie(CSRF_COOKIE);
    if (csrf) headers[CSRF_HEADER] = csrf;
  }

  const res = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail ?? data.error ?? detail;
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
