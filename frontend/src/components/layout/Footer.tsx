import { SinaMark } from "@/components/layout/SinaMark";

export function Footer() {
  return (
    <footer className="border-t border-sand-200 bg-sand-100">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <div className="flex items-center gap-2">
              <SinaMark className="size-7" />
              <span className="font-display text-lg font-semibold text-ink-900">
                Sina
              </span>
            </div>
            <p className="mt-2 text-sm text-ink-500">
              Información pública de precios para que las familias del norte de
              México cuiden su economía. Nombrada por el cactus sina, endémico de
              Sonora.
            </p>
          </div>
          <div className="text-sm text-ink-500">
            <p className="font-semibold text-ink-700">Fuentes oficiales</p>
            <p className="mt-1">Gasolina: CRE · Gas LP: CNE</p>
            <p>Supermercados: precios publicados por cada tienda</p>
          </div>
        </div>
        <p className="mt-8 text-xs text-ink-500">
          Sina es un proyecto sin fines de lucro. No almacenamos contraseñas.
        </p>
      </div>
    </footer>
  );
}
