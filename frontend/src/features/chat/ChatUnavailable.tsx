import { Link } from "react-router-dom";

import { SinaMark } from "@/components/layout/SinaMark";

/**
 * El backend del chat (Fase 3: POST /api/v1/chat + LLMProvider) aún no existe.
 * Mostramos un estado "próximamente" deliberado, con el botón deshabilitado.
 * Cuando el backend exista, esta pantalla se reemplaza por la UI conversacional
 * sin cambiar la ruta.
 */
export default function ChatUnavailable() {
  return (
    <section className="mx-auto flex max-w-2xl flex-col items-center px-4 py-20 text-center">
      <SinaMark className="size-16" />
      <span className="mt-6 rounded-full bg-brand-600/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-200">
        Próximamente
      </span>
      <h1 className="mt-4 text-3xl md:text-4xl">El asistente de Sina</h1>
      <p className="mt-3 max-w-lg text-lg text-ink-700">
        Pronto podrás preguntarle a Sina dónde ahorrar, con tus propias palabras.
        Estamos afinando las respuestas para que sean claras y fáciles de seguir.
      </p>

      <button
        type="button"
        disabled
        aria-disabled="true"
        title="Estará disponible pronto"
        className="mt-8 cursor-not-allowed rounded-full bg-sand-200 px-6 py-3 font-semibold text-ink-500"
      >
        Abrir asistente — próximamente
      </button>

      <p className="mt-6 text-sm text-ink-500">
        Mientras tanto, ya puedes{" "}
        <Link to="/gasolina" className="font-semibold text-brand-600 hover:underline dark:text-brand-300">
          comparar precios de gasolina
        </Link>{" "}
        o{" "}
        <Link
          to="/supermercados"
          className="font-semibold text-brand-600 hover:underline dark:text-brand-300"
        >
          buscar en la despensa
        </Link>
        .
      </p>
    </section>
  );
}
