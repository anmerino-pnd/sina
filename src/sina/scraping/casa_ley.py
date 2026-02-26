import os
import re
import json
import time
import datetime
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from sina.config.paths import CASA_LEY_DATA
from sina.config.credentials import casa_ley_url as CASA_LEY_URL

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def extract_images(driver) -> set[str]:
    """Extracts high-res image URLs from current page view."""
    urls = set()
    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    for img in soup.select('img.left, img.right'):
        src = img.get('src', '')
        if 'publitas' in src:
            high_res = re.sub(r'-at\d+', '-at2400', src)
            urls.add(high_res)
    
    return urls


def discover_pages(base_url: str) -> dict[int, str]:
    """
    Opens page/1, clicks next until the end.
    Returns {page_number: image_url}
    """
    print(f"🔍 Opening: {base_url}")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    pages = {}
    
    try:
        driver.get(base_url)
        time.sleep(3)
        
        # Esperar a que cargue la primera imagen
        try:
            wait.until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "img.left, img.right")
            ))
            print("✅ First image loaded.")
        except TimeoutException:
            print("❌ No images found on first page.")
            return pages
        
        page_num = 1
        
        while True:
            # Capturar imagen actual para detectar cambio
            try:
                current_src = driver.find_element(
                    By.CSS_SELECTOR, "img.left, img.right"
                ).get_attribute('src')
            except:
                current_src = ""
            
            # Extraer URLs de esta vista
            new_urls = extract_images(driver)
            for url in new_urls:
                if url not in pages.values():
                    pages[page_num] = url
                    print(f"📄 Page {page_num}: ✅")
                    page_num += 1
            
            # Intentar ir a la siguiente página
            try:
                next_btn = driver.find_element(By.ID, "next_slide")
                
                btn_class = next_btn.get_attribute('class') or ""
                if 'disabled' in btn_class:
                    print("🔚 Last page reached (button disabled).")
                    break
                
                driver.execute_script("arguments[0].click();", next_btn)
                
                # Esperar a que cambie la imagen
                try:
                    wait.until(
                        lambda d: d.find_element(
                            By.CSS_SELECTOR, "img.left, img.right"
                        ).get_attribute('src') != current_src
                    )
                    time.sleep(0.5)
                except TimeoutException:
                    print("🔚 Image didn't change. End of flyer.")
                    break
                    
            except NoSuchElementException:
                print("🔚 No 'next' button found. End of flyer.")
                break
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        driver.quit()
        print(f"\n📊 Total pages: {len(pages)}")
    
    return pages


def download_flyer(base_url: str, city: str, base_dir: str) -> bool:
    """
    Discovers all pages via Selenium, downloads images, saves metadata.
    """
    print(f"🚀 Downloading flyer for: {city}")
    
    # 1. Descubrir páginas
    pages = discover_pages(base_url)
    
    if not pages:
        print("\n⚠️ No pages found.")
        return False
    
    # 2. Preparar directorio
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().isoformat()
    
    clean_city = (
        city.lower()
        .replace(" ", "_")
        .replace("á", "a").replace("é", "e")
        .replace("í", "i").replace("ó", "o").replace("ú", "u")
    )
    output_dir = os.path.join(base_dir, clean_city, today)
    os.makedirs(output_dir, exist_ok=True)
    
    # 3. Descargar imágenes
    print(f"\n--- Downloading {len(pages)} images to: {output_dir} ---")
    success = 0
    
    metadata = {
        "city": city,
        "extracting_date": timestamp,
        "base_url": base_url,
        "total_pages_found": len(pages),
        "pages": {}
    }
    
    for page_num, img_url in sorted(pages.items()):
        try:
            file_name = f"page_{page_num:02d}.jpg"
            file_path = os.path.join(output_dir, file_name)
            
            response = requests.get(img_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ {file_name} ({len(response.content) // 1024} KB)")
            success += 1
            
            metadata['pages'][file_name] = {
                "source_url": img_url,
                "page_url": f"{base_url}/page/{page_num}",
                "size_bytes": len(response.content)
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Page {page_num}: {e}")
    
    # 4. Metadata
    metadata['total_pages_downloaded'] = success
    metadata['status'] = (
        "success" if success == len(pages)
        else "partial" if success > 0
        else "failed"
    )
    
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Metadata: {metadata_path}")
    print(f"✅ {success}/{len(pages)} downloaded")
    print("🎉 ¡Success!" if success == len(pages) else "⚠️ Some pages failed")
    
    return success == len(pages)
