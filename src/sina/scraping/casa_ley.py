import os
import re
import time
import json
import requests
import datetime
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from sina.config.paths import CASA_LEY_DATA
from sina.config.credentials import casa_ley_url as CASA_LEY_URL

# ==================== CONFIGURACIÓN ====================
CIUDAD_OBJETIVO = "Hermosillo"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
CARPETA_SALIDA = CASA_LEY_DATA


def select_city(driver, wait, city: str):
    """
    Searches and clicks the city's button using robust JS clicks.
    """
    print(f"🏙️ Searching city's button: {city}...")
    
    try:
        # 1. Buscamos cualquier elemento que contenga la ciudad
        xpath = f"//button[contains(text(), '{city}')] | //a[contains(text(), '{city}')] | //option[contains(text(), '{city}')] | //*[contains(@class, 'tab') and contains(text(), '{city}')]"
        
        elements = driver.find_elements(By.XPATH, xpath)
        
        for el in elements:
            # Solo interactuar con elementos que realmente se ven en pantalla
            if el.is_displayed():
                # Inyectar JS Click es 100x más seguro que el click() normal de Selenium
                driver.execute_script("arguments[0].click();", el)
                
                # Si el elemento era un dropdown (<option>), forzamos al navegador a detectar el cambio
                if el.tag_name == 'option':
                    parent = el.find_element(By.XPATH, "..")
                    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", parent)
                    
                print(f"✅ City '{city}' found and clicked.")
                return True
                
        # 2. Estrategia de respaldo (Búsqueda amplia en todo el texto)
        amplio_xpath = f"//*[normalize-space(text())='{city}']"
        respaldos = driver.find_elements(By.XPATH, amplio_xpath)
        for el in respaldos:
            if el.is_displayed() and el.tag_name not in ['script', 'style']:
                driver.execute_script("arguments[0].click();", el)
                print(f"✅ City '{city}' clicked (Fallback strategy).")
                return True

        print(f"❌ No visible button found for '{city}'.")
        return False
        
    except Exception as e:
        print(f"❌ Error clicking city: {e}")
        return False


def iframe_publitas_wait(driver, wait):
    """
    Switches the context to the publitas iframe.
    """
    print("⏳ Switching context to iframe...")
    try:
        iframe = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                'iframe[src*="publitas.com"], iframe[src*="view.publitas"]'
            ))
        )
        driver.switch_to.frame(iframe)
        print("✅ Context switched to iframe.")
        return True
    except TimeoutException:
        print("❌ iframe not found.")
        return False


def get_url_pages(driver, wait):
    """
    Get the urls of every image on iframe.
    """
    urls_folleto = set()
    
    try:
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "img.left, img.right")))
        print("✅ Initial flyer image found.")
    except TimeoutException:
        print("⚠️ Initial flyer image not found, next...")
    
    page_num = 1
    
    while True:
        try:
            try:
                imagen_actual = driver.find_element(By.CSS_SELECTOR, "img.left, img.right").get_attribute('src')
            except:
                imagen_actual = ""
            
            # Parsing
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            # Extracting all images
            new_found = 0
            for img in soup.select('img.left, img.right'):
                url_down = img.get('src')
                if url_down and 'publitas' in url_down:
                    url_up = re.sub(r'-at\d+', '-at2400', url_down)
                    if url_up not in urls_folleto:
                        print(f"📄 Page {page_num} found: {url_up[:80]}...")
                        urls_folleto.add(url_up)
                        page_num += 1
                        new_found += 1
            
            try:
                next_button = driver.find_element(By.ID, "next_slide")
                
                button_class = next_button.get_attribute('class') or ""
                if 'disabled' in button_class:
                    print("🔚 End of the flyer.")
                    break
                
                print("▶️ Next page...")
                
                driver.execute_script("arguments[0].click();", next_button)
                
                time.sleep(1)  
                wait.until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "img.left, img.right").get_attribute('src') != imagen_actual
                )
                
            except NoSuchElementException:
                print("🔚 'Next' button not found. Ending.")
                break
            except TimeoutException:
                if new_found == 0:
                    print("🔚 No more pages found. Ending.")
                    break
                print("⏱️ Waiting page to change...")
                time.sleep(1)
                continue
                
        except Exception as e:
            print(f"⚠️ Error: {type(e).__name__}: {e}")
            break
    
    return urls_folleto


def get_imgs(main_url: str, urls: set, base_dir: str, city: str) -> bool:
    """
    Downloading imgs from flyer: base_dir / city / YYYY-MM-DD /
    """
    if not urls:
        print("\n⚠️ No urls were found to download.")
        return False

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    exact_timestamp = datetime.datetime.now().isoformat()
    
    clean_city = city.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    object_dir = os.path.join(base_dir, clean_city, today)
    
    os.makedirs(object_dir, exist_ok=True)

    urls_list = sorted(list(urls))
    print(f"\n--- Downloading {len(urls_list)} imgs in: {object_dir} ---")
    success_download = 0
    
    metadata = {
        "city": city,
        "extracting_date": exact_timestamp,
        "url": {
            "main_url": main_url
        },
        "total_pages_found": len(urls_list),
        "pages": {} 
    }

    for i, url in enumerate(urls_list, start=1):
        try:
            file_name = os.path.join(object_dir, f"page_{i:02d}.jpg")
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"✅ Saved: {file_name}")
            success_download += 1
            
            metadata['pages'][f'page_{i:02d}.jpg'] = url
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error {url}: {e}")

    metadata['total_pages_downloaded'] = success_download
    metadata['status'] = "success" if success_download == len(urls_list) else "partial" if success_download > 0 else "failed"
    
    metadata_file = os.path.join(object_dir, "metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=True)

    print(f"\n📋 Metadata saved: {metadata_file}")
    print(f"✅ {success_download}/{len(urls_list)} pages downloaded successfully")
    print("\n🎉 ¡Success!")

    if success_download == len(urls_list):
        return True
    else:
        return False


def get_ley_flyer(city: str, url: str, folder: str) -> bool:
    """
    Scraps and downloads imgs from the url.
    
    Args:
        City: Name of the city, must coincide with the name in the web page.
    """
    print(f"🚀 Scraping flyer from city: {city}")
    print(f"📍 URL: {url}")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080") 
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    flyer_url = set()
    
    try:
        driver.get(url)
        print("✅ Page charged.")
        time.sleep(4) # Dar tiempo a que cargue la estructura de React/Angular
        
        # 1. CAPTURAR IFRAME VIEJO: Leemos qué iframe hay ANTES de dar clic
        old_src = ""
        try:
            old_iframe = driver.find_element(By.CSS_SELECTOR, 'iframe[src*="publitas.com"]')
            old_src = old_iframe.get_attribute("src")
            print(f"ℹ️ Default iframe loaded: {old_src[:50]}...")
        except:
            pass
        
        # 2. HACER CLIC EN LA CIUDAD
        # OJO: Pasamos 'driver' como primer argumento para poder usar JS Clicks
        if not select_city(driver, wait, city):
            print("❌ No se pudo seleccionar la ciudad. Abortando.")
            return False
        
        # 3. ESPERAR A QUE EL IFRAME CAMBIE
        print("⏳ Waiting for the flyer iframe to update to the new city...")
        time.sleep(5) # Crucial: Esperar a que la red descargue el nuevo iframe
        
        if old_src:
            try:
                # Le decimos a Selenium que no avance hasta que el link sea diferente al de La Paz
                wait.until(lambda d: d.find_element(By.CSS_SELECTOR, 'iframe[src*="publitas.com"]').get_attribute('src') != old_src)
                print("✅ Iframe source successfully updated!")
            except TimeoutException:
                print("⚠️ Iframe source did not change. It might be the same flyer or the click failed.")

        # 4. ENTRAR AL IFRAME NUEVO Y EXTRAER
        if not iframe_publitas_wait(driver, wait):
            print("❌ iframe unavailable. Aborting.")
            return False
        
        flyer_url = get_url_pages(driver, wait)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("\n🔒 Closing web page.")
    
    return get_imgs(url, flyer_url, folder, city=city)