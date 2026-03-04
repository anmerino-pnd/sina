import re
import time
import json
import ollama
from toon import encode
from ollama import Client
from typing import Optional, List
from sina.config.paths import DATA
from sina.config.credentials import ollama_api_key
from pydantic import ValidationError, BaseModel, Field
from sina.config.prompt import extract_text_prompt, clean_response

client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + ollama_api_key}
)

def extract_text(supermarket: str, city: str, date: str, 
                cloud: bool = True,
                model: str = "qwen3.5:397b-cloud"):

    path = DATA / supermarket / city / date / "recortes"
    imgs = []
    for img_path in path.iterdir():
        imgs.append(img_path)

    batch_size = 1
    flyer = {
    "products": [],
    "start_date": None,
    "end_date": None,
    "store": supermarket,
    "legal_warnings": None,
    "extra_info": None
}

    for i in range(0, len(imgs), batch_size):
        batch = imgs[i:i + batch_size]
        batch_num = i // batch_size + 1
        messages = [
                {
                    'role': 'system',
                    'content': encode(extract_text_prompt)
                },
                {
                    'role': 'user',
                    'content': f'Analiza las siguientes imágenes y extrae la información del supermercado {supermarket}',
                    'images': batch
                }
            ]
        
        try: 
            print(f"\n⏳ Enviando batch {batch_num} a Ollama (Contiene {len(batch)} imágenes)...")
            start_time = time.time()
            match cloud:
                case True:
                    flyer_text = client.chat(
                        model = model,
                        messages = messages,
                        options = {'temperature': 0}
                    )
                case False:
                    flyer_text = ollama.chat(
                        model = model,
                        messages = messages,
                        options = {'temperature': 0}
                    )
            elapsed_time = time.time() - start_time
            print(f"✅ Ollama respondió en {elapsed_time:.2f} segundos.")

            batch_data  = clean_response(flyer_text.message.content)

            print(batch_data)

            if batch_data.get("products"):
                flyer["products"].extend(batch_data["products"])
                print(f"  Batch {batch_num}: {len(batch_data['products'])} productos")
                
            for key in ["start_date", "end_date", "legal_warnings", "extra_info"]:
                new_value = batch_data.get(key)
                
                if new_value and not flyer.get(key):
                    flyer[key] = new_value
                
                elif new_value and flyer.get(key) and key in ["legal_warnings", "extra_info"]:
                    if new_value not in flyer[key]:
                        flyer[key] = f"{flyer[key]} | {new_value}"
                
        except json.JSONDecodeError as e:
            print(f"✗ Error parseando JSON en batch {batch_num}: {e}")
        except ValidationError as e:
            print(f"✗ Error de validación en batch {batch_num}: {e}")
        except Exception as e:
            print(f"✗ Error procesando batch {batch_num}: {e}")

    flyer['total_products'] = len(flyer['products'])
    print(f"\nTotal de productos extraídos: {len(flyer['products'])}")

    path = DATA / supermarket / city / date / "flyer_data.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(flyer, f, ensure_ascii=False, indent= 3)
    