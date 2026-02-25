import os
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

qqp_url : str = os.getenv('QQP_DATOS_URL')
datos_abiertos_url: str = os.getenv('DATOS_ABIERTOS_URL')
gasolina_hmo_url: str = os.getenv('GASOLINA_HMO_URL')
casa_ley_url: str = os.getenv('CASA_LEY_URL')

class BoundingBox(BaseModel):
    label: str
    x: int
    y: int
    w: int
    h: int

class AnnotationPayload(BaseModel):
    store_name: str       
    image_filename: str   
    boxes: List[BoundingBox]

class FlyerPayload(BaseModel):
    supermarket: str
    city: str