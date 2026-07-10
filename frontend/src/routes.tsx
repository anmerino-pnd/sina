import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";

import { App } from "@/App";
import { PageFallback } from "@/components/layout/PageFallback";

// Code-splitting por ruta: la landing no carga el código de los dashboards.
const LandingPage = lazy(() => import("@/pages/LandingPage"));
const GasolinaPage = lazy(() => import("@/features/gasolina/GasolinaPage"));
const GasLpPage = lazy(() => import("@/features/gasLp/GasLpPage"));
const SupermercadosPage = lazy(() => import("@/features/supermercados/SupermercadosPage"));
const ChatPage = lazy(() => import("@/features/chat/ChatPage"));
const NotFound = lazy(() => import("@/pages/NotFound"));

function withSuspense(node: React.ReactNode) {
  return <Suspense fallback={<PageFallback />}>{node}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: withSuspense(<LandingPage />) },
      { path: "gasolina", element: withSuspense(<GasolinaPage />) },
      { path: "gas-lp", element: withSuspense(<GasLpPage />) },
      { path: "supermercados", element: withSuspense(<SupermercadosPage />) },
      { path: "chat", element: withSuspense(<ChatPage />) },
      { path: "*", element: withSuspense(<NotFound />) },
    ],
  },
]);
