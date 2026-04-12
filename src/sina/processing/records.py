import pandas as pd

def _to_float(x) -> float | None:
    """
    Convierte a float tolerando:
    - NaN / None
    - Strings con comas decimales: "23,45" → 23.45
    - Strings con símbolo de peso: "$23.45" → 23.45
    - Strings con espacios
    """
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(x, str):
        x = x.strip().replace("$", "").replace(",", ".").replace(" ", "")
        if x == "" or x == "-":
            return None
    try:
        return float(x)
    except (ValueError, TypeError):
        return None

def df_to_dict(
    df: pd.DataFrame,
    column_map: dict[str, str] | None = None,
    float_cols: list[str] | None = None,
    datetime_cols: list[str] | None = None,
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
    # DESPUÉS
    if float_cols:
        for col in float_cols:
            if col in df.columns:
                df[col] = df[col].apply(_to_float)

    for col in df.columns:
        df = df[df[col].astype(str) != col]

    # 2.6 Parsear columnas de fecha si existen
    if datetime_cols:
        for col in datetime_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                # Filas donde la fecha no se pudo parsear las eliminamos
                df = df[df[col].notna()]

    # 3. Convertir a lista de dicts
    registros = df.to_dict(orient="records")

    # 4. Agregar campos extra a cada registro
    if extra_fields:
        for registro in registros:
            registro.update(extra_fields)

    return registros