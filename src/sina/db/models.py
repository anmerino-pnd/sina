# src/sina/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class PrecioQQP(Base):
    __tablename__ = 'qqp_precios'

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto = Column(String, nullable=False)
    presentacion = Column(String, nullable=False)
    marca = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    catalogo = Column(String, nullable=True)
    precio = Column(Float, nullable=False)
    fecha_registro = Column(DateTime, nullable=False)
    cadena_comercial = Column(String, nullable=True)
    giro = Column(String, nullable=True)
    nombre_comercial = Column(String, nullable=True)
    direccion = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    municipio = Column(String, nullable=False)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)

# sina/db/models.py
class PrecioGasolina(Base):
    __tablename__ = "gasolineras"

    numero    = Column(String, primary_key=True)  # PL/11257/EXP/ES/2015
    estado    = Column(String, nullable=False)
    municipio = Column(String, nullable=False)

    # ── Fase 1: scraping (nullable hasta que llegue CRE) ──
    latitud   = Column(Float,  nullable=True)
    longitud  = Column(Float,  nullable=True)

    # ── Fase 2: CRE API (nullable hasta que llegue scraping) ──
    nombre    = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    magna     = Column(Float,  nullable=True)
    premium   = Column(Float,  nullable=True)
    diesel    = Column(Float,  nullable=True)

    fecha_registro = Column(DateTime, nullable=True)