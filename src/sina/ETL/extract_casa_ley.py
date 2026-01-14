import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from sina.settings.config import CASA_LEY_DATA , HEADERS
from sina.settings.credentials import casa_ley 

CARPETA_SALIDA = CASA_LEY_DATA

def descargar_folleto_ley():
    """
    Descarga todas las páginas del folleto de Casa Ley.
    Retorna la lista de archivos descargados.
    """
    urls_folleto = set()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # modo headless moderno
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(casa_ley)
        wait = WebDriverWait(driver, 20)
        print("⏳ Esperando que el iframe del folleto se cargue...")

        iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*="publitas.com"]')))
        driver.switch_to.frame(iframe)
        print("✅ Iframe encontrado. Accediendo al folleto...")

        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "left")))
        print("✅ Folleto inicial cargado.")

        while True:
            imagen_actual = driver.find_element(By.CSS_SELECTOR, "img.left").get_attribute('src') or ""

            soup = BeautifulSoup(driver.page_source, 'lxml')
            for img in soup.select('img.left, img.right'):
                url_baja = img.get('src')
                if url_baja and 'publitas' in url_baja:
                    url_alta = re.sub(r'-at\d+', '-at2400', url_baja)
                    if url_alta not in urls_folleto:
                        print(f"📄 Página encontrada: {url_alta}")
                        urls_folleto.add(url_alta)

            try:
                next_button = driver.find_element(By.ID, "next_slide")
                if 'disabled' in next_button.get_attribute('class'):
                    print("🔚 Fin del folleto.")
                    break

                print("▶️ Pasando a la siguiente página...")
                next_button.click()
                wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "img.left").get_attribute('src') != imagen_actual)

            except Exception:
                print("⚠️ No se pudo avanzar. Terminando.")
                break

    finally:
        driver.quit()
        print("\nNavegador cerrado.")

    archivos = []
    lista_urls = sorted(urls_folleto)

    if lista_urls:
        print(f"\n--- Iniciando descarga de {len(lista_urls)} imágenes ---")
        timestamp = datetime.now().strftime("%d%m%Y")

        for i, url in enumerate(lista_urls, start=1):
            nombre_archivo = os.path.join(CARPETA_SALIDA, f"pagina_{i:02d}_{timestamp}.jpg")
            try:
                response = requests.get(url, headers=HEADERS, timeout=30)
                response.raise_for_status()
                with open(nombre_archivo, 'wb') as f:
                    f.write(response.content)
                archivos.append(nombre_archivo)
                print(f"✅ Guardada: {nombre_archivo}")
            except requests.exceptions.RequestException as e:
                print(f"❌ Error al descargar {url}: {e}")

        print("\n🎉 ¡Proceso completado!")
        return archivos
    else:
        print("\nNo se encontraron URLs para descargar.")
        return []
