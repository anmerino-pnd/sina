import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { obtenerHealth } from "@/lib/api/health";
import { formatearFecha } from "@/lib/format";
import type { HealthDominio } from "@/lib/types";

interface Seccion {
  to: string;
  titulo: string;
  descripcion: string;
  dominio?: keyof Omit<
    Awaited<ReturnType<typeof obtenerHealth>>,
    "status"
  >;
  disponible: boolean;
}

const SECCIONES: Seccion[] = [
  {
    to: "/gasolina",
    titulo: "Gasolina",
    descripcion:
      "Compara Magna, Premium y Diésel por estación y encuentra la más barata cerca de ti.",
    dominio: "gasolina",
    disponible: true,
  },
  {
    to: "/gas-lp",
    titulo: "Gas LP",
    descripcion:
      "Precio por kilo de cada permisionario en tu localidad, en recipientes y autotanques.",
    dominio: "gas_lp",
    disponible: true,
  },
  {
    to: "/supermercados",
    titulo: "Supermercados",
    descripcion:
      "Busca productos de la despensa y descubre en qué tienda salen más baratos.",
    dominio: "supermercados",
    disponible: true,
  },
];

function Frescura({ dato }: { dato?: HealthDominio }) {
  if (!dato?.ultima_actualizacion) return null;
  return (
    <p className="mt-3 text-xs text-ink-500">
      Actualizado el {formatearFecha(dato.ultima_actualizacion)}
    </p>
  );
}

export default function LandingPage() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: obtenerHealth,
    staleTime: 5 * 60_000,
  });

  return (
    <>
      {/* Hero editorial: violeta como acento, no como fondo. */}
      <section className="mx-auto max-w-6xl px-4 pb-8 pt-14 md:pt-20">
        <p className="font-medium uppercase tracking-[0.18em] text-sage-600">
          Sonora · información pública
        </p>
        <h1 className="mt-3 max-w-3xl text-4xl md:text-6xl">
          Gasta menos en lo de{" "}
          <span className="text-brand-600 dark:text-brand-300">primera necesidad</span>.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-ink-700">
          Sina reúne los precios de gasolina, gas LP y despensa de fuentes
          oficiales y las tiendas, para que tu familia decida dónde comprar más
          barato. Gratis y sin registro.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/gasolina"
            className="rounded-full bg-brand-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-brand-700"
          >
            Ver precios de gasolina
          </Link>
          <Link
            to="/supermercados"
            className="rounded-full border border-sand-300 bg-surface px-6 py-3 font-semibold text-ink-700 transition-colors hover:bg-sand-100"
          >
            Buscar en la despensa
          </Link>
        </div>
      </section>

      {/* Tarjetas de secciones */}
      <section className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid gap-4 md:grid-cols-3">
          {SECCIONES.map((s) => (
            <Link
              key={s.to}
              to={s.to}
              className="group flex flex-col rounded-[var(--radius-card)] border border-sand-200 bg-surface p-6 shadow-[var(--shadow-card)] transition-transform hover:-translate-y-0.5"
            >
              <h2 className="text-2xl text-ink-900">{s.titulo}</h2>
              <p className="mt-2 flex-1 text-sm text-ink-700">
                {s.descripcion}
              </p>
              <Frescura dato={s.dominio ? health?.[s.dominio] : undefined} />
              <span className="mt-4 text-sm font-semibold text-brand-600 group-hover:text-brand-700 dark:text-brand-300">
                Explorar →
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* Cómo funciona */}
      <section className="mx-auto max-w-6xl px-4 py-10">
        <div className="grid gap-8 md:grid-cols-3">
          {[
            {
              n: "1",
              t: "Elige tu municipio",
              d: "Selecciona dónde vives; Sina trae los precios vigentes de esa zona.",
            },
            {
              n: "2",
              t: "Compara al instante",
              d: "Verás de menor a mayor precio, con la fecha del dato y de dónde viene.",
            },
            {
              n: "3",
              t: "Decide y ahorra",
              d: "Ubica lo más barato cerca de ti y calcula cuánto te ahorras.",
            },
          ].map((paso) => (
            <div key={paso.n}>
              <span className="font-display text-3xl text-flare-500">
                {paso.n}
              </span>
              <h3 className="mt-1 text-lg text-ink-900">{paso.t}</h3>
              <p className="mt-1 text-sm text-ink-700">{paso.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Teaser del chat (próximamente) */}
      <section className="mx-auto max-w-6xl px-4 pb-16">
        <div className="rounded-[var(--radius-card)] border border-brand-100 bg-brand-50 p-8">
          <span className="rounded-full bg-brand-600/10 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-brand-700 dark:text-brand-200">
            Próximamente
          </span>
          <h2 className="mt-3 max-w-2xl text-2xl text-ink-900">
            Pregúntale a Sina con tus propias palabras
          </h2>
          <p className="mt-2 max-w-2xl text-ink-700">
            Estamos construyendo un asistente para que cualquiera —sin importar
            qué tan fácil se le den las apps— pueda preguntar “¿dónde está más
            barata la leche?” y recibir una respuesta clara.
          </p>
          <Link
            to="/chat"
            className="mt-5 inline-block text-sm font-semibold text-brand-700 hover:underline dark:text-brand-200"
          >
            Conocer el asistente →
          </Link>
        </div>
      </section>
    </>
  );
}
