import time
import ollama
from toon import encode
from pathlib import Path
from typing import Optional, List
from sina.config.paths import DATA
from pydantic import BaseModel, Field

from sina.config.prompt import (
    Product,
    FlyerExtraction,
    extract_text_prompt
)

def extract_text(
        supermarket: str,
        city: str,
        date: str
):
    
    path = DATA / supermarket / city / date / "recortes"

    imgs = []
    for img_path in path.iterdir():
        imgs.append(img_path)

    batch_size = 2
    flyer = dict()

    for i in range(0, len(imgs), batch_size):
        batch = imgs[i:i + batch_size]
        messages = [
                {
                    'role': 'system',
                    'content': encode(extract_text_prompt)
                },
                {
                    'role': 'user',
                    'content': 'Analiza las siguientes imágenes y extrae la información',
                    'images': [batch]
                }
            ]
        
        flyer_text = ollama.chat(
            model="gemma3:27b",
            messages=messages,
            options={'temperature': 0},
            format= FlyerExtraction.model_json_schema()
        )
    pass