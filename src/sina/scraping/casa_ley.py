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

from sina.config.settings import CASA_LEY_DATA
from sina.config.credentials import casa_ley as CASA_LEY_URL

# ==================== CONFIGURACIÓN ====================
CIUDAD_OBJETIVO = "Hermosillo"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
CARPETA_SALIDA = CASA_LEY_DATA


def select_city(wait, city: str):
    """
    Searches and clicks the city's button
    """
    print(f"🏙️ Searching city's button: {city}...")
    
    try:
        city_button = wait.until(
            EC.element_to_be_clickable((
                By.XPATH, 
                f"//button[contains(text(), '{city}')] | //a[contains(text(), '{city}')] | //*[contains(@class, 'tab') and contains(text(), '{city}')]"
            ))
        )
        city_button.click()
        print(f"✅ City '{city}' found.")
        return True
    except TimeoutException:
        pass


def iframe_publitas_wait(driver, wait):
    """
    Wait until publitas iframe changes and updates the page.
    """
    print("⏳ Waiting iframe...")
    
    time.sleep(2)
    
    # Search iframe
    try:
        iframe = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                'iframe[src*="publitas.com"], iframe[src*="view.publitas"]'
            ))
        )
        driver.switch_to.frame(iframe)
        print("✅ iframe found.")
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
        print("✅ Initial flyer found..")
    except TimeoutException:
        print("⚠️ Initial flyer not found, next...")
    
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


def get_imgs(main_url: str, urls: set, base_dir: str, city: str):
    """
    Downloading imgs from flyer: base_dir / city / YYYY-MM-DD /
    """
    if not urls:
        print("\n⚠️ No urls were found to download.")
        return

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    exact_timestamp = datetime.datetime.now().isoformat()
    
    clean_city = city.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    object_dir = os.path.join(base_dir, clean_city, today)
    
    os.makedirs(object_dir, exist_ok=True)

    urls_list = sorted(list(urls))
    print(f"\n--- Downloading {len(urls_list)} imgs in: {object_dir} ---")
    success_download = 0

    for i, url in enumerate(urls_list):
        try:
            file_name = os.path.join(object_dir, f"page_{i+1:02d}.jpg")
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"✅ Saved: {file_name}")
            success_download += 1
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error {url}: {e}")

    metadata = {
        "city": city,
        "extracting_date": exact_timestamp,
        "url": main_url,
        "total_pages_found": len(urls_list),
        "total_pages_downloaded": success_download,
        "status": "success" if success_download == len(urls_list) else "failed"

    }

    print("\n🎉 ¡Success!")


def get_flyer(city: str, url: str, folder: str):
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
        
        time.sleep(3) 
        
        if not select_city(wait, city):
            print("❌ No se pudo seleccionar la ciudad. Abortando.")
            return
        
        time.sleep(2)
        
        if not iframe_publitas_wait(driver, wait):
            print("❌ iframe unavailable. Aborting.")
            return
        
        flyer_url = get_url_pages(driver, wait)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("\n🔒 Closing web page.")
    
    get_imgs(url, flyer_url, folder, city=city)

    
