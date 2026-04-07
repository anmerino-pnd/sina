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

class PrecioGasolina(Base):
    __tablename__ = "precio_gasolina"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    estado      = Column(String, nullable=False)   # "Sonora"
    municipio   = Column(String, nullable=False)
    numero      = Column(String, nullable=False)  # PL/10156/EXP/ES/2015
    nombre      = Column(String, nullable=False)
    direccion   = Column(String, nullable=True)
    diesel      = Column(Float,  nullable=True)
    magna       = Column(Float,  nullable=True)
    premium     = Column(Float,  nullable=True)
    latitud     = Column(Float,  nullable=True)
    longitud    = Column(Float,  nullable=True)
    fecha_registro = Column(DateTime)