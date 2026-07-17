"""
Backfill de embeddings para `supermercados`.

Los embeddings normalmente se generan al momento del upsert (scraping/flyer),
así que los productos insertados con ENABLE_EMBEDDINGS apagado — o con un modelo
anterior — quedan sin vector o con vectores de otro espacio. Este módulo los
(re)genera en lotes con el provider configurado (EMBEDDING_PROVIDER/EMBEDDING_MODEL):

    ENABLE_EMBEDDINGS=1 uv run python -m sina.embedder.backfill            # solo faltantes
    ENABLE_EMBEDDINGS=1 uv run python -m sina.embedder.backfill --todos    # regenerar TODO
                                                                           # (tras cambiar de modelo)
"""
from __future__ import annotations

import argparse
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from sina.config.credentials import DB_URL

log = logging.getLogger(__name__)

_LOTE = 128


def backfill_embeddings(solo_faltantes: bool = True) -> dict:
    """Devuelve un resumen {procesados, omitidos, lotes}."""
    if not DB_URL.startswith("postgresql"):
        raise RuntimeError("El backfill de embeddings requiere PostgreSQL (pgvector).")

    from sina.embedder.embeddings import get_embedding_service

    service = get_embedding_service()
    if service is None:
        raise RuntimeError(
            "Servicio de embeddings no disponible: corre con ENABLE_EMBEDDINGS=1 y "
            "el modelo descargado (ollama pull qwen3-embedding:8b)."
        )

    from sina.db.models import Supermercado
    from sina.db.repository import SupermercadoRepository

    repo = SupermercadoRepository(db_url=DB_URL)
    resumen = {"procesados": 0, "lotes": 0}

    with Session(repo.engine) as session:
        stmt = select(Supermercado)
        if solo_faltantes:
            stmt = stmt.where(Supermercado.embedding.is_(None))
        filas = session.scalars(stmt).all()
        print(f"[+] Productos a vectorizar: {len(filas)}"
              f" ({'solo sin embedding' if solo_faltantes else 'todos'})")

        for i in range(0, len(filas), _LOTE):
            lote = filas[i:i + _LOTE]
            dicts = [
                {"producto": f.producto, "tienda": f.tienda, "precio": float(f.precio or 0.0)}
                for f in lote
            ]
            vectores = service.vectorizar_productos(dicts)
            for fila, vector in zip(lote, vectores):
                fila.embedding = vector
            session.commit()
            resumen["procesados"] += len(lote)
            resumen["lotes"] += 1
            print(f"  [+] {resumen['procesados']}/{len(filas)}")

    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="(Re)genera embeddings de supermercados.")
    parser.add_argument(
        "--todos", action="store_true",
        help="regenera TODOS los vectores (default: solo los productos sin embedding)",
    )
    args = parser.parse_args()
    print(backfill_embeddings(solo_faltantes=not args.todos))
