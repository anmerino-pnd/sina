import json
import requests
import pandas as pd
from pathlib import Path
from datetime import date
from sina.config.paths import GAS_DATA
from sina.config.credentials import gasolina_api_rest, cne_refere

GAS_COLUMN_MAP = {
    "Numero":    "numero",
    "Nombre":    "nombre",
    "Direccion": "direccion",
    "Diesel":    "diesel",
    "Magna":     "magna",
    "Premium":   "premium",
    "Latitud":   "latitud",
    "Longitud":  "longitud",
}

GAS_FLOAT_COLS = ["diesel", "magna", "premium", "latitud", "longitud"]

MUNICIPIOS_JSON = GAS_DATA / Path("catalogo_municipios.json")

with open(MUNICIPIOS_JSON, "r", encoding="utf-8") as f:
    mun_dict = json.load(f)

def extract_gas_prices(estado: str, municipio: str) -> dict:
    params = {
        "entidadId"  : mun_dict[estado]['id'],
        "municipioId": mun_dict[estado]['municipios'][municipio].get('id')
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

def df_gas_prices(estado: str, municipio: str) -> pd.DataFrame:
    data = extract_gas_prices(estado, municipio)
    df_cne = pd.DataFrame(data["Value"])

    print(f"Columnas disponibles: {df_cne.columns.tolist()}")
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
        index   = ["Numero", "Nombre", "Direccion"],
        columns = "Combustible",
        values  = "PrecioVigente",
        aggfunc = "first"
    ).reset_index()

    df_pivot.columns.name = None

    for col in ["Magna", "Premium", "Diesel"]:
        if col not in df_pivot.columns:
            df_pivot[col] = None

    CACHE_FILE = GAS_DATA / municipio / Path(f"gasolineras_{municipio}.json")
    
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        gas_dict = json.load(f)

    df_pivot["Latitud"] = df_pivot["Numero"].map(
    lambda x: gas_dict.get(x, {}).get("Latitud")
)

    df_pivot["Longitud"] = df_pivot["Numero"].map(
        lambda x: gas_dict.get(x, {}).get("Longitud")
    )
    
    return df_pivot
