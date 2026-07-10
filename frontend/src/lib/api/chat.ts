import { apiFetch, csrfHeader } from "@/lib/api/client";

export interface UbicacionChat {
  estado?: string;
  municipio?: string;
  localidad?: string;
  lat?: number;
  lng?: number;
}

export interface MensajeHistorial {
  rol: "user" | "assistant";
  contenido: string;
}

export interface MetadatosRespuesta {
  modelo: string;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number | null;
  tokens_por_segundo: number | null;
  duracion_ms: number;
  fecha_pregunta: string;
  tool_timings: { tool: string; ms: number }[];
  phase_timings: { llm_ms: number; tools_ms: number; total_ms: number; iteraciones: number };
}

export interface Conversacion {
  id: string;
  titulo: string;
  num_mensajes: number;
  ultimo_preview: string;
  actualizado_en: string | null;
}

export interface ChunkMensajes {
  chunk_id: string | null;
  anterior_id: string | null;
  mensajes: { rol: string; contenido: string; metadatos?: MetadatosRespuesta; ts?: string }[];
}

interface EnviarArgs {
  mensaje: string;
  conversacionId?: string | null;
  historial?: MensajeHistorial[];
  ubicacion?: UbicacionChat;
  signal?: AbortSignal;
  onPaso?: (tool: string) => void;
  onToken?: (texto: string) => void;
  onError?: (detalle: string) => void;
}

interface ResultadoChat {
  conversacionId: string | null;
  metadatos: MetadatosRespuesta | null;
}

/**
 * Envía un mensaje y consume la respuesta en streaming (SSE). El `signal` permite
 * pausar/abortar; al abortar, el backend NO persiste el intercambio.
 */
export async function enviarMensajeStream(args: EnviarArgs): Promise<ResultadoChat> {
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...csrfHeader() },
    body: JSON.stringify({
      mensaje: args.mensaje,
      conversacion_id: args.conversacionId ?? undefined,
      historial: args.historial,
      ubicacion: args.ubicacion,
    }),
    signal: args.signal,
  });

  if (!res.ok || !res.body) {
    let detalle = `Error ${res.status}`;
    try {
      const d = await res.json();
      detalle = d.detail ?? d.error ?? detalle;
    } catch {
      /* sin cuerpo */
    }
    args.onError?.(detalle);
    return { conversacionId: args.conversacionId ?? null, metadatos: null };
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let resultado: ResultadoChat = { conversacionId: args.conversacionId ?? null, metadatos: null };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Los eventos SSE se separan por línea en blanco.
    const bloques = buffer.split("\n\n");
    buffer = bloques.pop() ?? "";
    for (const bloque of bloques) {
      const evento = parseSse(bloque);
      if (!evento) continue;
      if (evento.tipo === "token") args.onToken?.(evento.dato.texto ?? evento.dato);
      else if (evento.tipo === "paso") args.onPaso?.(evento.dato.tool);
      else if (evento.tipo === "error") args.onError?.(evento.dato.detalle ?? "error");
      else if (evento.tipo === "done") {
        resultado = {
          conversacionId: evento.dato.conversacion_id ?? resultado.conversacionId,
          metadatos: evento.dato.metadatos ?? null,
        };
      }
    }
  }
  return resultado;
}

function parseSse(bloque: string): { tipo: string; dato: any } | null {
  let tipo = "message";
  const datos: string[] = [];
  for (const linea of bloque.split("\n")) {
    if (linea.startsWith("event:")) tipo = linea.slice(6).trim();
    else if (linea.startsWith("data:")) datos.push(linea.slice(5).trim());
  }
  if (!datos.length) return null;
  try {
    return { tipo, dato: JSON.parse(datos.join("\n")) };
  } catch {
    return { tipo, dato: datos.join("\n") };
  }
}

// ── Conversaciones (requieren sesión) ──────────────────────────────────
export function listarConversaciones(): Promise<{ conversaciones: Conversacion[] }> {
  return apiFetch("/chat/conversaciones");
}

export function crearConversacion(titulo?: string): Promise<Conversacion> {
  return apiFetch("/chat/conversaciones", { method: "POST", body: { titulo } });
}

export function borrarConversacion(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/chat/conversaciones/${id}`, { method: "DELETE" });
}

export function cargarMensajes(id: string, chunk?: string): Promise<ChunkMensajes> {
  const qs = chunk ? `?chunk=${encodeURIComponent(chunk)}` : "";
  return apiFetch(`/chat/conversaciones/${id}/mensajes${qs}`);
}
