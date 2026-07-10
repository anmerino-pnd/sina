import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { IconPin } from "@/components/ui/icons";
import { useUbicacionUsuario } from "@/hooks/useUbicacionUsuario";
import { ApiError } from "@/lib/api/client";
import {
  borrarConversacion,
  cargarMensajes,
  crearConversacion,
  enviarMensajeStream,
  listarConversaciones,
  type Conversacion,
  type MetadatosRespuesta,
} from "@/lib/api/chat";

interface Msg {
  rol: "user" | "assistant";
  contenido: string;
  metadatos?: MetadatosRespuesta;
  detenido?: boolean;
}

function aMsg(m: { rol: string; contenido: string; metadatos?: MetadatosRespuesta }): Msg {
  return {
    rol: m.rol === "assistant" ? "assistant" : "user",
    contenido: m.contenido,
    metadatos: m.metadatos,
  };
}

function actualizarUltimo(msgs: Msg[], fn: (m: Msg) => Msg): Msg[] {
  if (!msgs.length) return msgs;
  const copia = msgs.slice();
  copia[copia.length - 1] = fn(copia[copia.length - 1]);
  return copia;
}

export default function ChatPage() {
  const { user } = useAuth();
  const { ubicacion, tieneCoords, buscando, pedirUbicacion } = useUbicacionUsuario();

  const [mensajes, setMensajes] = useState<Msg[]>([]);
  const [entrada, setEntrada] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [paso, setPaso] = useState<string | null>(null);
  const [conversacionId, setConversacionId] = useState<string | null>(null);
  const [conversaciones, setConversaciones] = useState<Conversacion[]>([]);
  const [anteriorId, setAnteriorId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const finRef = useRef<HTMLDivElement | null>(null);

  const refrescarConversaciones = useCallback(async () => {
    if (!user) return;
    try {
      const { conversaciones } = await listarConversaciones();
      setConversaciones(conversaciones);
    } catch {
      /* sin historial (Mongo no disponible) */
    }
  }, [user]);

  useEffect(() => {
    refrescarConversaciones();
  }, [refrescarConversaciones]);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, paso]);

  async function abrirConversacion(id: string) {
    setConversacionId(id);
    try {
      const chunk = await cargarMensajes(id);
      setMensajes(chunk.mensajes.map(aMsg));
      setAnteriorId(chunk.anterior_id);
    } catch {
      setMensajes([]);
      setAnteriorId(null);
    }
  }

  async function cargarAnteriores() {
    if (!conversacionId || !anteriorId) return;
    const chunk = await cargarMensajes(conversacionId, anteriorId);
    setMensajes((prev) => [...chunk.mensajes.map(aMsg), ...prev]);
    setAnteriorId(chunk.anterior_id);
  }

  async function nuevaConversacion() {
    setConversacionId(null);
    setMensajes([]);
    setAnteriorId(null);
    if (user) {
      try {
        const conv = await crearConversacion();
        setConversacionId(conv.id);
        await refrescarConversaciones();
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          alert(e.detail); // tope de conversaciones alcanzado
        }
      }
    }
  }

  async function eliminar(id: string) {
    await borrarConversacion(id);
    if (id === conversacionId) {
      setConversacionId(null);
      setMensajes([]);
    }
    refrescarConversaciones();
  }

  async function enviar() {
    const texto = entrada.trim();
    if (!texto || enviando) return;
    setEntrada("");
    const historial = mensajes.slice(-8).map((m) => ({ rol: m.rol, contenido: m.contenido }));
    setMensajes((prev) => [...prev, { rol: "user", contenido: texto }, { rol: "assistant", contenido: "" }]);
    setEnviando(true);
    setPaso(null);

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const r = await enviarMensajeStream({
        mensaje: texto,
        conversacionId,
        historial,
        ubicacion: {
          estado: ubicacion.estado,
          municipio: ubicacion.municipio,
          localidad: ubicacion.localidad,
          lat: ubicacion.lat,
          lng: ubicacion.lng,
        },
        signal: ctrl.signal,
        onToken: (t) => setMensajes((prev) => actualizarUltimo(prev, (m) => ({ ...m, contenido: m.contenido + t }))),
        onPaso: (tool) => setPaso(tool),
        onError: (d) =>
          setMensajes((prev) => actualizarUltimo(prev, (m) => ({ ...m, contenido: m.contenido || `⚠ ${d}` }))),
      });
      if (r.conversacionId && r.conversacionId !== conversacionId) setConversacionId(r.conversacionId);
      if (r.metadatos) setMensajes((prev) => actualizarUltimo(prev, (m) => ({ ...m, metadatos: r.metadatos! })));
      if (user) refrescarConversaciones();
    } catch (e) {
      if (ctrl.signal.aborted) {
        setMensajes((prev) => actualizarUltimo(prev, (m) => ({ ...m, detenido: true })));
      } else {
        setMensajes((prev) =>
          actualizarUltimo(prev, (m) => ({ ...m, contenido: m.contenido || "⚠ No pude responder." })),
        );
      }
    } finally {
      setEnviando(false);
      setPaso(null);
      abortRef.current = null;
    }
  }

  function pausar() {
    abortRef.current?.abort();
  }

  const municipioTxt = ubicacion.municipio
    ? `${ubicacion.municipio}${ubicacion.estado ? `, ${ubicacion.estado}` : ""}`
    : null;

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-5xl gap-4 px-4 py-4">
      {/* Panel de conversaciones (solo con sesión) */}
      {user && (
        <aside className="hidden w-60 shrink-0 flex-col rounded-2xl border border-sand-200 bg-surface p-3 md:flex">
          <button
            onClick={nuevaConversacion}
            className="rounded-full bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            + Nueva conversación
          </button>
          <ul className="mt-3 flex-1 space-y-1 overflow-y-auto">
            {conversaciones.map((c) => (
              <li key={c.id}>
                <div
                  className={[
                    "group flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm",
                    c.id === conversacionId ? "bg-brand-50 text-brand-700 dark:text-brand-200" : "text-ink-700 hover:bg-sand-100",
                  ].join(" ")}
                >
                  <button className="min-w-0 flex-1 truncate text-left" onClick={() => abrirConversacion(c.id)}>
                    {c.titulo || c.ultimo_preview || "Conversación"}
                  </button>
                  <button
                    onClick={() => eliminar(c.id)}
                    aria-label="Eliminar"
                    className="opacity-0 group-hover:opacity-100 text-ink-400 hover:text-price-high"
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
            {conversaciones.length === 0 && (
              <li className="px-2 py-2 text-xs text-ink-500">Aún no tienes conversaciones.</li>
            )}
          </ul>
        </aside>
      )}

      {/* Columna principal */}
      <section className="flex min-w-0 flex-1 flex-col rounded-2xl border border-sand-200 bg-surface">
        {/* Chip de ubicación */}
        <div className="flex flex-wrap items-center gap-2 border-b border-sand-200 px-4 py-2.5 text-sm">
          <span className="text-ink-500">Ubicación:</span>
          <span className="font-medium text-ink-800">{municipioTxt ?? "sin municipio"}</span>
          <button
            onClick={pedirUbicacion}
            disabled={buscando}
            className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-sand-300 px-3 py-1 text-xs font-medium text-ink-700 hover:bg-sand-100"
            title="Compartir tu ubicación para buscar gasolina cerca de ti"
          >
            <IconPin />
            {buscando ? "Buscando…" : tieneCoords ? "Ubicación lista" : "Usar mi ubicación"}
          </button>
        </div>

        {/* Mensajes */}
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {anteriorId && (
            <div className="text-center">
              <button onClick={cargarAnteriores} className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-300">
                Cargar mensajes anteriores
              </button>
            </div>
          )}

          {mensajes.length === 0 && (
            <div className="mx-auto mt-10 max-w-md text-center text-ink-500">
              <p className="text-lg font-medium text-ink-800">Pregúntale a Sina</p>
              <p className="mt-2 text-sm">
                Ejemplos: “¿Dónde está la gasolina más barata en Hermosillo?”, “¿Cuánto cuesta la leche?”,
                “Arma la canasta más económica”.
              </p>
              {!user && (
                <p className="mt-4 text-xs">Inicia sesión con Google para guardar tu historial.</p>
              )}
            </div>
          )}

          {mensajes.map((m, i) => (
            <Burbuja key={i} msg={m} />
          ))}

          {paso && (
            <p className="text-xs italic text-ink-500">Usando {paso}…</p>
          )}
          <div ref={finRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-sand-200 p-3">
          <div className="flex items-end gap-2">
            <textarea
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  enviar();
                }
              }}
              rows={1}
              placeholder="Escribe tu pregunta…"
              className="max-h-32 flex-1 resize-none rounded-2xl border border-sand-300 bg-sand-50 px-4 py-2.5 text-sm text-ink-900 outline-none focus:border-brand-500"
            />
            {enviando ? (
              <button
                onClick={pausar}
                className="rounded-full border border-sand-300 px-4 py-2.5 text-sm font-semibold text-ink-700 hover:bg-sand-100"
                title="Pausar (no se guardará esta respuesta)"
              >
                Pausar
              </button>
            ) : (
              <button
                onClick={enviar}
                disabled={!entrada.trim()}
                className="rounded-full bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40"
              >
                Enviar
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function Burbuja({ msg }: { msg: Msg }) {
  const esUsuario = msg.rol === "user";
  const [verMeta, setVerMeta] = useState(false);
  return (
    <div className={esUsuario ? "flex justify-end" : "flex justify-start"}>
      <div className={["max-w-[80%] rounded-2xl px-4 py-2.5 text-sm", esUsuario ? "bg-brand-600 text-white" : "bg-sand-100 text-ink-900"].join(" ")}>
        <p className="whitespace-pre-wrap">
          {msg.contenido || (esUsuario ? "" : "…")}
          {msg.detenido && <span className="ml-1 text-xs italic opacity-70">(detenido)</span>}
        </p>
        {msg.metadatos && (
          <div className="mt-1.5 border-t border-ink-900/10 pt-1.5 text-[11px] opacity-70">
            <button onClick={() => setVerMeta((v) => !v)} className="hover:underline">
              {msg.metadatos.modelo} · {msg.metadatos.output_tokens} tok
              {msg.metadatos.tokens_por_segundo ? ` · ${msg.metadatos.tokens_por_segundo} tok/s` : ""}
            </button>
            {verMeta && (
              <div className="mt-1 space-y-0.5">
                <div>entrada: {msg.metadatos.input_tokens} tok · salida: {msg.metadatos.output_tokens} tok</div>
                <div>tiempo: {Math.round(msg.metadatos.duracion_ms)} ms · iteraciones: {msg.metadatos.phase_timings.iteraciones}</div>
                {msg.metadatos.tool_timings.length > 0 && (
                  <div>tools: {msg.metadatos.tool_timings.map((t) => `${t.tool} (${t.ms}ms)`).join(", ")}</div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
