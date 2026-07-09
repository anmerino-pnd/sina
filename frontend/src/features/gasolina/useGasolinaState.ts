import { useReducer } from "react";

import type { Categoria } from "@/lib/precios";
import type { TipoCombustible } from "@/lib/types";

export interface PuntoUsuario {
  lat: number;
  lng: number;
  manual: boolean;
}

export interface CalcState {
  tipo: "litros" | "pesos";
  monto: number;
}

export interface GasolinaState {
  fuel: TipoCombustible;
  filtroCategoria: Categoria | null;
  seleccionadoNumero: string | null; // estación en detalle + referencia de la calculadora
  baseNumero: string | null; // base de comparación de la calculadora
  punto: PuntoUsuario | null;
  modoFijar: boolean;
  calc: CalcState;
}

export const estadoInicial: GasolinaState = {
  fuel: "magna",
  filtroCategoria: null,
  seleccionadoNumero: null,
  baseNumero: null,
  punto: null,
  modoFijar: false,
  calc: { tipo: "litros", monto: 35 },
};

export type Accion =
  | { type: "SET_FUEL"; fuel: TipoCombustible }
  | { type: "TOGGLE_FILTRO"; categoria: Categoria }
  | { type: "SELECT"; numero: string }
  | { type: "DESELECT" }
  | { type: "SET_PUNTO"; punto: PuntoUsuario }
  | { type: "CLEAR_PUNTO" }
  | { type: "TOGGLE_MODO_FIJAR" }
  | { type: "SET_BASE"; numero: string }
  | { type: "RESET_BASE" }
  | { type: "SET_CALC_TIPO"; tipo: "litros" | "pesos" }
  | { type: "SET_CALC_MONTO"; monto: number }
  | { type: "RESET" };

function reducer(state: GasolinaState, a: Accion): GasolinaState {
  switch (a.type) {
    case "SET_FUEL":
      // Cambiar combustible resetea selección y base (igual que el JS actual).
      return { ...state, fuel: a.fuel, seleccionadoNumero: null, baseNumero: null };
    case "TOGGLE_FILTRO":
      return {
        ...state,
        filtroCategoria: state.filtroCategoria === a.categoria ? null : a.categoria,
      };
    case "SELECT":
      return { ...state, seleccionadoNumero: a.numero };
    case "DESELECT":
      return { ...state, seleccionadoNumero: null };
    case "SET_PUNTO":
      return { ...state, punto: a.punto, modoFijar: false };
    case "CLEAR_PUNTO":
      return { ...state, punto: null };
    case "TOGGLE_MODO_FIJAR":
      return { ...state, modoFijar: !state.modoFijar };
    case "SET_BASE":
      return {
        ...state,
        baseNumero: a.numero,
        // Si la referencia coincide con la nueva base, se limpia (como el original).
        seleccionadoNumero:
          state.seleccionadoNumero === a.numero ? null : state.seleccionadoNumero,
      };
    case "RESET_BASE":
      return { ...state, baseNumero: null };
    case "SET_CALC_TIPO":
      return {
        ...state,
        calc: { tipo: a.tipo, monto: a.tipo === "litros" ? 35 : 300 },
      };
    case "SET_CALC_MONTO":
      return { ...state, calc: { ...state.calc, monto: a.monto } };
    case "RESET":
      return estadoInicial;
    default:
      return state;
  }
}

export function useGasolinaState() {
  return useReducer(reducer, estadoInicial);
}
