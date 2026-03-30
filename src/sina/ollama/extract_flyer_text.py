import re
import time
import json
import ollama
from typing import cast
from toon import encode
from ollama import Client
from typing import Callable, Any
from sina.config.paths import DATA
from sina.config.credentials import ollama_api_key
from pydantic import ValidationError, BaseModel, Field
from sina.config.prompt import extract_text_prompt, clean_response

def extract_text(
    supermarket: str,
    city: str,
    date: str,
    cloud: bool = True,
    model: str = "qwen3.5:397b-cloud",
    batch_size: int = 1
) -> bool:

    try:
        input_path  = DATA / supermarket / city / date / "recortes"
        output_path = DATA / supermarket / city / date / "flyer_data.json"
        
        imgs = sorted(input_path.iterdir())

        if cloud:
            client = Client(
                host="https://ollama.com",
                headers={'Authorization': 'Bearer ' + ollama_api_key}
            )
            chat_fn: Callable[..., Any] = client.chat  
        else:
            chat_fn = ollama.chat

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
                    'images': [str(p) for p in batch]
                }
            ]

            try:
                print(f"\n⏳ Batch {batch_num}/{len(imgs)} ({len(batch)} imágenes)...")
                start_time = time.time()

                response = chat_fn(
                    model=model,
                    messages=messages,
                    options={'temperature': 0}
                )

                print(f"✅ Respondió en {time.time() - start_time:.2f}s")
                content: str | None = response.message.content
                if content is None:
                    print(f"⚠️ Batch {batch_num}: respuesta vacía")
                    continue
                
                batch_data = clean_response(content)

                if batch_data.get("products"):
                    flyer["products"].extend(batch_data["products"])
                    print(f"  → {len(batch_data['products'])} productos encontrados")

                for key in ["start_date", "end_date", "legal_warnings", "extra_info"]:
                    new_value = batch_data.get(key)
                    if not new_value:
                        continue
                    if not flyer.get(key):
                        flyer[key] = new_value
                    elif key in ["legal_warnings", "extra_info"]:
                        if new_value not in flyer[key]:
                            flyer[key] = f"{flyer[key]} | {new_value}"

            except json.JSONDecodeError as e:
                print(f"✗ Error JSON en batch {batch_num}: {e}")
            except ValidationError as e:
                print(f"✗ Error validación en batch {batch_num}: {e}")
            except Exception as e:
                print(f"✗ Error en batch {batch_num}: {e}")

        flyer['total_products'] = len(flyer['products'])
        print(f"\n📦 Total: {flyer['total_products']} productos")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(flyer, f, ensure_ascii=False, indent=3)

        print(f"✅ Datos guardados exitosamente en: {output_path}")
        return True

    except Exception as e:
        print(f"✗ Error crítico durante la extracción: {e}")
        return False