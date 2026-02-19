import os
from pydantic import BaseModel
from dotenv import load_dotenv

qqp : str = os.getenv('QQP_DATOS')
datos_abiertos: str = os.getenv('DATOS_ABIERTOS')
gasolina_hmo: str = os.getenv('GASOLINA_HMO')
casa_ley: str = os.getenv('CASA_LEY')