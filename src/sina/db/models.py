# src/sina/db/models.py
from sqlalchemy import (
    Column, Integer, String, Float, 
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
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

class EntidadFederativa(Base):
    """Catálogo de estados de México (CNE)."""
    __tablename__ = "cne_entidades"

    id        = Column(Integer, primary_key=True)   # el ID que da la CNE (01‑32)
    nombre    = Column(String, nullable=False)

    municipios = relationship("Municipio", back_populates="entidad")

    def __repr__(self):
        return f"<EntidadFederativa id={self.id} nombre={self.nombre}>"


class Municipio(Base):
    """Catálogo de municipios por entidad (CNE)."""
    __tablename__ = "cne_municipios"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    municipio_id = Column(String, nullable=False)   # ej. "030" — string porque viene con ceros
    nombre      = Column(String, nullable=False)
    entidad_id  = Column(Integer, ForeignKey("cne_entidades.id"), nullable=False)

    entidad    = relationship("EntidadFederativa", back_populates="municipios")
    localidades = relationship("Localidad", back_populates="municipio")

    __table_args__ = (
        UniqueConstraint("municipio_id", "entidad_id", name="uq_municipio_entidad"),
    )


class Localidad(Base):
    """Catálogo de localidades por municipio (CNE)."""
    __tablename__ = "cne_localidades"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    localidad_id = Column(Integer, nullable=False)   # el ID que da la CNE
    nombre       = Column(String, nullable=False)
    municipio_id = Column(Integer, ForeignKey("cne_municipios.id"), nullable=False)

    municipio = relationship("Municipio", back_populates="localidades")

    __table_args__ = (
        UniqueConstraint("localidad_id", "municipio_id", name="uq_localidad_municipio"),
    )

# sina/db/models.py

class GasLPPrecio(Base):
    """
    Precios de Gas LP por permisionario y localidad.
    Se actualiza semanalmente (cada sábado).
    
    Desnormalizado a propósito: guardamos nombres junto con IDs
    para evitar JOINs en consultas frecuentes de la UI.
    """
    __tablename__ = "gas_lp_precios"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Ubicación: IDs (para llamar a la CNE API) ──────────────
    entidad_id   = Column(Integer, nullable=False)
    municipio_id = Column(String,  nullable=False)  # ej. "030"
    localidad_id = Column(Integer, nullable=False)

    # ── Ubicación: Nombres (para mostrar en UI sin JOINs) ──────
    entidad_nombre   = Column(String, nullable=False)
    municipio_nombre = Column(String, nullable=False)
    localidad_nombre = Column(String, nullable=False)

    # ── Permisionario ──────────────────────────────────────────
    numero_permiso  = Column(String, nullable=False)
    marca_comercial = Column(String, nullable=True)

    # ── Tipo: "autotanque" | "recipiente" ──────────────────────
    tipo = Column(String, nullable=False)

    # ── Solo recipientes ───────────────────────────────────────
    capacidad_recipiente = Column(Integer, nullable=True)

    # ── Precio ─────────────────────────────────────────────────
    precio = Column(Float, nullable=False)

    # ── Control de caché ───────────────────────────────────────
    fecha_extraccion = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "entidad_id", "municipio_id", "localidad_id",
            "numero_permiso", "tipo", "capacidad_recipiente",
            name="uq_gas_lp_precio"
        ),
    )

    def __repr__(self):
        return (
            f"<GasLPPrecio {self.marca_comercial} | "
            f"{self.tipo} | ${self.precio} | "
            f"{self.municipio_nombre}, {self.entidad_nombre}>"
        )
    
    def esta_vigente(self, dias: int = 7) -> bool:
        """True si el precio fue extraído hace menos de `dias` días."""
        delta = datetime.utcnow() - self.fecha_extraccion
        return delta.days < dias