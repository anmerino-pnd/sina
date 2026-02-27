import time
import ollama
from typing import Optional, List
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(description="Nombre del producto tal como aparece en el flyer")
    brand: Optional[str] = Field(
        default=None,
        description="Marca del producto si es visible (ej: Bachoco, SuKarne, ETCO)"
    )
    price: Optional[float] = Field(
        default=None,
        description="Precio numérico del producto en oferta"
        )
    sale_type: Optional[str] = Field(
        description="Tipo de promoción aplicada al producto",
        examples=["precio_directo","2x1", "3x2", "2x$precio", "descuento"]
        )
    sale_description: Optional[str] = Field(
        default=None,
        description="Descripción literal de la oferta como aparece en el flyer",
        examples=["3x2 paga 2 y llévate 1 gratis", "30% de descuento", "a solo $49.90"]
    )
    unit: str = Field(
        description="Unidad de venta del producto",
        examples=["kilo", "litro", "pieza", "en bolsa", "mazo"]
        )
    restrictions: Optional[str] = Field(description="Restricciones de la oferta en cuestión")

class FlyerExtraction(BaseModel):
    products: List[Product]
    start_date: str = Field(
        description="Fecha de inicio de vigencia (formato YYYY-MM-DD)"
        )
    end_date : str = Field(
        description="Fecha de final de vigencia (formato YYYY-MM-DD)"
        )
    store: Optional[str] = Field(
        default=None,
        description="Nombre de la tienda (ej: Casa Ley, Walmart, Abarrey, etc.)"
    )
    legal_warnings: Optional[str] = Field(
        default=None,
        description="Texto legal o restricciones generales de las ofertas"
    )
    extra_info: Optional[str] = Field(
        default=None,
        description="Cualquier información adicional relevante fuera de los productos o restricciones generales"
    )

extract_text_prompt = {
    "rol": {
        "nombre": "Sina",
        "descripción": "Eres un sistema experto en extraer información de imágenes"
    },
    "objetivo": "Toda la información relevante de la imagen debe ser extraída y ordenada en el formato estipulado",
    "metodología": "Procesarás imágenes por batches "
}