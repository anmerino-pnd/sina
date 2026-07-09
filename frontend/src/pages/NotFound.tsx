import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="mx-auto max-w-2xl px-4 py-24 text-center">
      <p className="font-display text-6xl text-brand-600">404</p>
      <h1 className="mt-3 text-2xl">No encontramos esta página</h1>
      <p className="mt-2 text-ink-700">
        Puede que el enlace esté roto o que la sección aún no exista.
      </p>
      <Link
        to="/"
        className="mt-8 inline-block rounded-full bg-brand-600 px-6 py-3 font-semibold text-white hover:bg-brand-700"
      >
        Ir al inicio
      </Link>
    </section>
  );
}
