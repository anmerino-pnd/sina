import os
from typing import List, Any
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

qqp_url : str = os.getenv('QQP_DATOS_URL', "")
datos_abiertos_url: str = os.getenv('DATOS_ABIERTOS_URL', "")
gasolina_hmo_url: str = os.getenv('GASOLINA_HMO_URL', "")
casa_ley_url: str = os.getenv('CASA_LEY_URL', "")

ollama_api_key : str = os.getenv('OLLAMA_API_KEY', "")


class BoundingBox(BaseModel):
    label: str
    x: int
    y: int
    w: int
    h: int

class AnnotationPayload(BaseModel):
    supermarket: str
    city: str
    date: str
    image_name: str
    bboxes: List[BoundingBox]

class FlyerPayload(BaseModel):
    supermarket: str
    city: str

class ExtractPayload(BaseModel):
    supermarket: str
    city: str
    date: str