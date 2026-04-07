import os
import rarfile
import requests
import pandas as pd
from datetime import date

from bs4 import BeautifulSoup, Tag
from sina.config.credentials import (
    qqp_url,
    datos_abiertos_url, 
)

year = str(date.today().year)

QQP_COLUMN_MAP = {
    "PRODUCTO":        "producto",
    "PRESENTACION":    "presentacion",
    "MARCA":           "marca",
    "CATEGORIA":       "categoria",
    "CATALOGO":        "catalogo",
    "PRECIO":          "precio",
    "FECHAREGISTRO":   "fecha_registro",
    "CADENACOMERCIAL": "cadena_comercial",
    "GIRO":            "giro",
    "NOMBRECOMERCIAL": "nombre_comercial",
    "DIRECCION":       "direccion",
    "ESTADO":          "estado",
    "MUNICIPIO":       "municipio",
    "LATITUD":         "latitud",
    "LONGITUD":        "longitud",
}
QQP_FLOAT_COLS = ["precio", "latitud", "longitud"]

nombres_columnas = [
    'PRODUCTO',
    'PRESENTACION',
    'MARCA',
    'CATEGORIA',
    'CATALOGO',
    'PRECIO',
    'FECHAREGISTRO',
    'CADENACOMERCIAL',
    'GIRO',
    'NOMBRECOMERCIAL', # Cambiado de 'NOMBRE_SUCURSAL' para coincidir con tu lista
    'DIRECCION',
    'ESTADO', # Movido para coincidir con el orden
    'MUNICIPIO', # Movido para coincidir con el orden
    'LATITUD',
    'LONGITUD'
]

CHAR_MAP = {
    'é': 'ú',     # Azécar → Azúcar
    'à': 'ó',     # Jabàn → Jabón
    'ö': 'í',     # Maöz → Maíz
    'µ': 'á',     # Plµtano → Plátano
    '\x90': 'é',  # Caf\x90 → Café
    '¥': 'ñ',     # Pa¥ales → Pañales
}

def fix_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    for wrong, correct in CHAR_MAP.items():
        text = text.replace(wrong, correct)
    return text

def fix_df_encoding(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].apply(fix_text)
    return df

def extract_qqp() -> pd.DataFrame:
    df_qqp = pd.DataFrame()
    page = requests.get(qqp_url)
    soup = BeautifulSoup(page.content, 'lxml')

    download_link: str | None = None

    for link in soup.find_all('a'):
        if not isinstance(link, Tag):  
            continue
        if year in link.get_text():
            href = link.get('href')
            if href:
                download_link = str(href)
                break

    if download_link:
        url = "/".join([
            datos_abiertos_url.rstrip("/"),
            download_link.lstrip("/")
        ])

        rar_response = requests.get(url)
        rar_response.raise_for_status()

        with open('temp.rar', 'wb') as f:
            f.write(rar_response.content)

        with rarfile.RarFile('temp.rar') as rf:
            csv_files = [
                info for info in rf.infolist()
                if info.filename.lower().endswith('.csv') and year in info.filename
            ]

            if not csv_files:
                raise FileNotFoundError(f"No se encontraron CSVs con el año {year} en el RAR")

            newest_csv_info = max(csv_files, key=lambda x: x.date_time)

            print(f"📦 CSV más reciente: {newest_csv_info.filename}")
            print(f"🕒 Modificado: {newest_csv_info.date_time}")

            with rf.open(newest_csv_info) as csv_file_in_rar:
                df_qqp = pd.read_csv(
                    csv_file_in_rar,
                    encoding='utf-8',
                    header=None,
                    low_memory=False
                )

    os.remove('temp.rar')
    df_qqp.columns = nombres_columnas
    df_qqp = fix_df_encoding(df_qqp)

    return df_qqp
