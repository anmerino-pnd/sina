import json
import requests
import pandas as pd
from pathlib import Path
from datetime import date
from sina.config.paths import GAS_DATA
from sina.config.credentials import gasolina_api_rest, cne_refere

MUNICIPIOS_JSON = GAS_DATA / Path("catalogo_municipios.json")

with open(MUNICIPIOS_JSON, "r", encoding="utf-8") as f:
    mun_dict = json.load(f)

def gas_prices(estado: str, ciudad: str) -> dict:
    params = {
        "entidadId"  : mun_dict[estado]['id'],
        "municipioId": mun_dict[estado]['municipios'][ciudad].get('id')
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer"   : cne_refere
    }
    response = requests.get(gasolina_api_rest, params=params, headers=headers)
    print(f"Status  : {response.status_code}")
    print(f"Size    : {len(response.content) / 1024:.1f} KB")
    print(f"Content : {response.headers.get('Content-Type')}")

    data = response.json()

    if isinstance(data, list):
        print(f"Registros : {len(data)}")
    elif isinstance(data, dict):
        print(f"Keys : {list(data.keys())}")

    return dict(data)

def df_gas_prices(estado: str, ciudad: str) -> pd.DataFrame:
    data = gas_prices(estado, ciudad)
    df_cne = pd.DataFrame(data["Value"])

    mapa_productos = {
        sp: (
            "Premium" if "Premium" in sp
            else "Magna"  if "Regular" in sp
            else "Diesel" if "Diésel"  in sp
            else "Otro"
        )
        for sp in df_cne["SubProducto"].unique()
    }

    for k, v in mapa_productos.items():
        print(f"  {v:10} ← {k}")

    df_cne["Combustible"] = df_cne["SubProducto"].map(mapa_productos)

    df_pivot = df_cne.pivot_table(
        index   = ["Numero", "Nombre", "Direccion", "Latitud", "Longitud"],
        columns = "Combustible",
        values  = "PrecioVigente",
        aggfunc = "first"
    ).reset_index()

    df_pivot.columns.name = None

    for col in ["Magna", "Premium", "Diesel"]:
        if col not in df_pivot.columns:
            df_pivot[col] = None

    return df_pivot

def df_to_dict(
    df: pd.DataFrame,
    estado: str,
    ciudad: str
) -> list[dict]:
    """Convierte el DataFrame a lista de dicts para bulk insert."""
    hoy = date.today()
    registros = []

    for _, row in df.iterrows():
        registros.append({
            "estado"        : estado,
            "municipio"     : ciudad,
            "numero"        : row["Numero"],
            "nombre"        : row["Nombre"],
            "direccion"     : row.get("Direccion"),
            "diesel"        : None if pd.isna(row["Diesel"])   else float(row["Diesel"]),
            "magna"         : None if pd.isna(row["Magna"])    else float(row["Magna"]),
            "premium"       : None if pd.isna(row["Premium"])  else float(row["Premium"]),
            "latitud"       : None if pd.isna(row["Latitud"])  else float(row["Latitud"]),
            "longitud"      : None if pd.isna(row["Longitud"]) else float(row["Longitud"]),
            "fecha_registro": hoy,
        })

    return registros