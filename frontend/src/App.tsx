import { Outlet, ScrollRestoration } from "react-router-dom";

import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";

export function App() {
  return (
    <div className="flex min-h-dvh flex-col bg-sand-50">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-brand-600 focus:px-4 focus:py-2 focus:text-white"
      >
        Saltar al contenido
      </a>
      <Navbar />
      <main id="contenido" className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <ScrollRestoration />
    </div>
  );
}
