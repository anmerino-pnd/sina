import re
import json

flyer_schema = {
    "products": {
        "type": "list",
        "description": "Lista de productos",
        "items": {
            "name": {
                "type": "str",
                "required": True,
                "description": "Nombre del producto tal como aparece en el flyer"
            },
            "brand": {
                "type": "str",
                "required": False,
                "description": "Marca del producto si tiene y es visible (ej: Bachoco, SuKarne, ETCO)"
            },
            "price": {
                "type": "float",
                "required": False,
                "description": "Precio numérico del producto en oferta"
            },
            "sale_type": {
                "type": "str",
                "required": False,
                "description": "Tipo de promoción aplicada al producto",
                "examples": ["precio_directo", "2x1", "3x2", "2x$precio", "descuento"]
            },
            "sale_description": {
                "type": "str",
                "required": False,
                "description": "Descripción literal de la oferta como aparece en el flyer",
                "examples": ["3x2 paga 2 y llévate 1 gratis", "30% de descuento", "a solo $49.90"]
            },
            "unit": {
                "type": "str",
                "required": False,
                "description": "Unidad de venta del producto",
                "examples": ["kilo", "litro", "pieza", "en bolsa", "mazo"]
            },
            "restrictions": {
                "type": "str",
                "required": False,
                "description": "Restricciones de la oferta en cuestión"
            }
        }
    },
    "start_date": {
        "type": "str",
        "required": False,
        "description": "Fecha de inicio de precios y ofertas válidas (formato YYYY-MM-DD)"
    },
    "end_date": {
        "type": "str",
        "required": False,
        "description": "Fecha de final de precios y ofertas válidas (formato YYYY-MM-DD)"
    },
    "store": {
        "type": "str",
        "required": False,
        "description": "Nombre de la tienda (ej: casa_ley, walmart, abarrey, etc.)"
    },
    "legal_warnings": {
        "type": "str",
        "required": False,
        "description": "Texto legal o restricciones generales de las ofertas"
    },
    "extra_info": {
        "type": "str",
        "required": False,
        "description": "Cualquier información adicional relevante fuera de los productos o restricciones generales"
    }
}

extract_text_prompt = {
    "rol": {
        "nombre": "Sina",
        "descripción": "eres un sistema experto en visión computacional y extracción de datos estructurados de flyers de supermercados",
        "objetivo": "analizar las imágenes proporcionadas y extraer toda la información relevante de productos, precios, vigencias y avisos, estructurándola estrictamente en el formato JSON requerido",
    },
    "reglas": {
        'fidelidad': 'extrae el texto tal cual aparece en la imagen. No inventes nombres de productos, marcas o precios',
        'informacion_parcial': 'estás evaluando recortes de un folleto más grande. si la imagen actual solo contiene productos y no menciona fechas de vigencia ni el nombre de la tienda, debes retornar esos campos como nulos (`null`)',
        'no_deduzcas': 'rellena el formato SOLO con la información visualmente presente en las imágenes de esta petición',
        'clasificacion_promos': 'presta especial atención a la mecánica de la oferta (ej. "3x2", "lleva 2 por $X", "descuento") y colócala en el campo correspondiente'
    },
    "formato_respuesta": {
        "instrucción": "responde ÚNICAMENTE con el objeto JSON. SIN markdown, SIN ```json, SIN explicaciones. Empieza directamente con { y termina con }",
        "campos_opcionales": "cualquier campo que NO sea visible en la imagen debe ser `null`. No todos los recortes contienen todos los campos — eso es esperado y correcto"
    },
    "flyer_schema": flyer_schema
}

def clean_response(raw: str) -> dict:
    """Extrae el JSON de la respuesta, con o sin markdown wrapping."""
    clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip())
    return json.loads(clean)