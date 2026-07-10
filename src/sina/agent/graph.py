"""
Motor de grafo mínimo (estilo LangGraph, sin dependencias).

Un `Grafo` tiene nodos (funciones `state -> dict` de actualización parcial),
aristas fijas y aristas condicionales (un router `state -> nombre_nodo`). Los
nodos pueden ser **generadores** que ceden eventos de streaming y devuelven la
actualización de estado con `return` — así el mismo grafo sirve para orquestar y
para transmitir tokens en vivo.

Uso:
    g = Grafo()
    g.add_node("agente", nodo_agente)
    g.add_node("tools", nodo_tools)
    g.set_entry("agente")
    g.add_conditional_edges("agente", router, {"tools": "tools", END: END})
    g.add_edge("tools", "agente")
    for evento in g.stream(estado):   # cede lo que cedan los nodos
        ...
    # estado final ya mutado in-place
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Iterator

END = "__end__"

Nodo = Callable[[dict], Any]           # -> dict | generador que retorna dict
Router = Callable[[dict], str]


class Grafo:
    def __init__(self) -> None:
        self._nodos: dict[str, Nodo] = {}
        self._aristas: dict[str, str] = {}
        self._condicionales: dict[str, tuple[Router, dict[str, str]]] = {}
        self._entrada: str | None = None

    def add_node(self, nombre: str, fn: Nodo) -> None:
        self._nodos[nombre] = fn

    def set_entry(self, nombre: str) -> None:
        self._entrada = nombre

    def add_edge(self, origen: str, destino: str) -> None:
        self._aristas[origen] = destino

    def add_conditional_edges(self, origen: str, router: Router, mapping: dict[str, str]) -> None:
        self._condicionales[origen] = (router, mapping)

    def _siguiente(self, actual: str, state: dict) -> str:
        if actual in self._condicionales:
            router, mapping = self._condicionales[actual]
            clave = router(state)
            return mapping.get(clave, END)
        return self._aristas.get(actual, END)

    def stream(self, state: dict) -> Iterator[Any]:
        """Ejecuta el grafo cediendo los eventos que produzcan los nodos."""
        if self._entrada is None:
            raise RuntimeError("El grafo no tiene nodo de entrada (set_entry).")

        actual = self._entrada
        while actual != END:
            fn = self._nodos[actual]
            resultado = fn(state)
            if inspect.isgenerator(resultado):
                actualizacion = yield from resultado   # cede eventos; captura el return
            else:
                actualizacion = resultado
            if actualizacion:
                state.update(actualizacion)
            actual = self._siguiente(actual, state)
