import pandas as pd
from typing import Callable

def df_to_dict(
    df: pd.DataFrame,
    column_map: dict[str, str] | None = None,
    float_cols: list[str] | None = None,
    extra_fields: dict | None = None,
) -> list[dict]:
    """
    Convierte un DataFrame a lista de dicts para bulk insert.

    Args:
        df:           DataFrame de entrada.
        column_map:   Renombra columnas { "NOMBRE_DF": "nombre_db" }.
        float_cols:   Columnas que deben castearse a float (con None si NaN).
        extra_fields: Campos extra a agregar a cada registro { "estado": "Sonora" }.
    """
    # 1. Renombrar columnas si se especifica
    if column_map:
        df = df.rename(columns=column_map)

    # 2. Castear columnas float y manejar NaN
    if float_cols:
        for col in float_cols:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: None if pd.isna(x) else float(x)
                )

    # 3. Convertir a lista de dicts
    registros = df.to_dict(orient="records")

    # 4. Agregar campos extra a cada registro
    if extra_fields:
        for registro in registros:
            registro.update(extra_fields)

    return registros