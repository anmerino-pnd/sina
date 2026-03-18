import logging
import requests
import pandas as pd
from bs4.element import Tag
from bs4 import BeautifulSoup
from sina.config.credentials import gasolina_hmo_url

def extract_gas() -> pd.DataFrame:
    logging.info("Getting table...")
    page = requests.get(gasolina_hmo_url, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "lxml")

    rows = []
    for tr in soup.find_all("tr"):
        if not isinstance(tr, Tag):
            continue
            
        tds = tr.find_all("td", attrs={"data-label": True})
        if not tds:
            continue
            
        row = {}
        for td in tds:

            if not isinstance(td, Tag):
                continue
                
            label = td.attrs.get("data-label") 
            if label: 
                row[label] = td.get_text(strip=True)
        
        rows.append(row)

    df = pd.DataFrame(rows)
    logging.info(f"Gas: {df.shape}")
    return df
