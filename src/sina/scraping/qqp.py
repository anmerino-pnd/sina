import os
import logging
import requests
import rarfile
import pandas as pd

from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup

from sina.config.credentials import qqp, datos_abiertos
year = str(date.today().year)


TEMP_FILE = Path("temp.rar")

COLUMNAS = [
    'PRODUCTO', 'PRESENTACION', 'MARCA', 'CATEGORIA', 'CATALOGO',
    'PRECIO', 'FECHAREGISTRO', 'CADENACOMERCIAL', 'GIRO',
    'NOMBRECOMERCIAL', 'DIRECCION', 'ESTADO', 'MUNICIPIO',
    'LATITUD', 'LONGITUD'
]

def extract_qqp(year: str = year) -> pd.DataFrame:
    logging.info("Looking for RAR file from QQP...")
    page = requests.get(qqp, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "lxml")

    download_link = None
    for link in soup.find_all("a"):
        if year in link.text:
            download_link = link["href"]
            break
    if not download_link:
        raise ValueError(f"Not link was found for year: {year}")

    url = os.path.join(datos_abiertos, download_link)
    logging.info(f"Dowloading: {url}")

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(TEMP_FILE, "wb") as f:
        f.write(response.content)

    with rarfile.RarFile(TEMP_FILE) as rf:
        csv_name = rf.namelist()[-2]
        logging.info(f"Reading CSV {csv_name}")
        with rf.open(csv_name) as csv_file_in_rar:
            df = pd.read_csv(csv_file_in_rar, encoding="utf-8", header=None)

    TEMP_FILE.unlink(missing_ok=True)
    df.columns = COLUMNAS
    logging.info(f"QQP: {df.shape}")
    return df
