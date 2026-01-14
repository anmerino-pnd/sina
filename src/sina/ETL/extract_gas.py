import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sina.settings.credentials import gasolina_hmo

def extract_gas() -> pd.DataFrame:
    logging.info("Extrayendo tabla gasolina...")
    page = requests.get(gasolina_hmo, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "lxml")

    rows = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", attrs={"data-label": True})
        if not tds:
            continue
        row = {td["data-label"]: td.get_text(strip=True) for td in tds}
        rows.append(row)

    df = pd.DataFrame(rows)
    logging.info(f"Gasolina: {df.shape}")
    return df
