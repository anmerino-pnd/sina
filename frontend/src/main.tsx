import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { router } from "@/routes";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { aplicarTema, temaInicial } from "@/lib/theme";
import "@/styles/index.css";

// Aplica el tema antes del primer render (evita parpadeo; sin script inline por CSP).
aplicarTema(temaInicial());

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // El backend ya cachea agresivamente; evitamos refetches de más.
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("No se encontró el elemento #root");

createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
