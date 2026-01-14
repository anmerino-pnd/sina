from typing import Tuple
from string import Template
from abc import ABC, abstractmethod
from datetime import date

current_date = date.today().isoformat()

class SupermarketOCRBase(ABC):
    @abstractmethod
    def extract_text(self, image_path: str) -> dict:
        """With the help of a MultiModal model, extract the text from the image"""
        pass

    def system_prompt(self) -> str:
        return(
f"""
Eres un extractor de datos de folletos de supermercados.
Tu tarea es analizar la imagen y devolver SOLO un objeto JSON válido con esta estructura:

{
  "productos": [
    {
      "nombre": "string | null",
      "precio": "string | null",
      "oferta": "string | null",
      "presentacion": "string | null",
      "limites": "string | null",
      "condiciones": "string | null"
    }
  ],
  "vigencia": "string | null",
  "sucursales": "string | null",
  "detalles": "string | null"
}

Reglas:
- Responde SOLO con JSON, sin texto extra.
- Omite productos incompletos o ilegibles.
- Usa `null` si un campo no aparece.
- No inventes información.
"""

        )
    
    def slicing_window(self, image_path: str, folder_path: str, window_height: int, overlap: int):
        """If the image is too big, try slicing it"""
        pass