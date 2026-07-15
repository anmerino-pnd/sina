# src/sina/db/models.py
from sqlalchemy import (
    DateTime, Date, ForeignKey, UniqueConstraint, Index,
    Column, Integer, String, Float, Boolean, Text, JSON
)
from sqlalchemy.orm import declarative_base, relationship, mapped_column
from sina.config.timezone import get_mexico_now, to_mexico_tz
from datetime import datetime, timedelta, timezone
from pgvector.sqlalchemy import Vector
from typing import cast

Base = declarative_base()

# PrecioQQP (PROFECO / "Quién es Quién en los Precios") fue eliminado en jul 2026:
# la fuente se reemplazó por scraping directo (`Supermercado`). La tabla
# `qqp_precios` puede quedar huérfana en DBs existentes (create_all no borra).

class CatalogoConfig(Base):
    """
    Configura las rutas activas de Soriana.
    Cada registro define una URL completa que el scraper debe visitar.
    """
    __tablename__ = "catalogos_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tienda = Column(String, nullable=False, default="Soriana")
    departamento = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    url_path = Column(String, nullable=False)  # Ej: "/despensa/arroz-frijol-y-semillas/arroz/"
    activo = Column(Boolean, default=True)
    prioridad = Column(Integer, default=1)
    ultima_extraccion = Column(DateTime(timezone=True), nullable=True)
    fecha_registro = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("tienda", "departamento", "categoria", "url_path", name="uq_catalogo"),
        Index("ix_catalogo_activo", "activo"),
        Index("ix_catalogo_prioridad", "prioridad"),
    )

    def __repr__(self):
        return (
            f"<CatalogoConfig id={self.id} "
            f"tienda='{self.tienda}' "
            f"departamento='{self.departamento}' "
            f"categoria='{self.categoria}' "
            f"url_path='{self.url_path}'>"
        )
    

class Supermercado(Base):
    """
    Productos + precios de supermercado. Unifica dos fuentes (`fuente`):
      - "scraping": sitios de tienda (Soriana/Del Sol/Benavides/Guadalajara),
        identidad estable por `pid` (único); precio de anaquel permanente.
      - "flyer": volantes (Casa Ley…) extraídos por VLM; NO traen `pid` (por eso
        `pid` es nullable) y son PROMOS temporales → llevan `vigencia_inicio/fin`.
        Su dedup es por la clave compuesta `uq_super_flyer`.
    """
    __tablename__ = 'supermercados'

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    # pid: identidad del scraping. Nullable porque los flyers no lo tienen.
    pid = Column(Integer, nullable=True, unique=True)
    tienda = Column(String, default="Soriana")
    departamento = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    subcategoria = Column(String, nullable=True)
    # Discriminador de origen + campos propios del flyer (nullable para scraping).
    fuente = Column(String, nullable=False, default="scraping", server_default="scraping")
    marca = Column(String, nullable=True)
    unidad = Column(String, nullable=True)
    vigencia_inicio = Column(Date, nullable=True)
    vigencia_fin = Column(Date, nullable=True)
    embedding = mapped_column(Vector(), nullable=True)
    fecha_actualizacion = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # Dedup de flyer (coexiste con el unique de `pid` para scraping):
        # un producto por tienda/fuente/inicio de vigencia.
        UniqueConstraint("tienda", "producto", "fuente", "vigencia_inicio",
                         name="uq_super_flyer"),
        Index("ix_supermercado_pid", "pid"),
        Index("ix_supermercado_departamento", "departamento"),
        Index("ix_supermercado_categoria", "categoria"),
        Index("ix_supermercado_fuente", "fuente"),
    )

    def __repr__(self):
        return (
            f"<Supermercado(id={self.id}, producto='{self.producto}', "
            f"precio={self.precio}, tienda='{self.tienda}', fuente='{self.fuente}', "
            f"departamento='{self.departamento}', categoria='{self.categoria}')>"
            )

# sina/db/models.py
class PrecioGasolina(Base):
    __tablename__ = "gasolineras"
    __table_args__ = (
        Index("ix_gas_estado_mun", "estado", "municipio"),
    )

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

    def __repr__(self):
        return (
            f"<PrecioGasolina {self.numero} | "
            f"{self.municipio}, {self.estado} | "
            f"magna={self.magna} premium={self.premium} diesel={self.diesel}>"
        )

    def esta_vigente(self) -> bool:
        """
        Gasolina se actualiza casi diario.
        Consideramos vigente si tiene menos de 24 horas.
        """
        if self.fecha_registro is None:
            return False
        fecha: datetime = cast(datetime, self.fecha_registro)
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        fecha_mx = to_mexico_tz(fecha)
        ahora_mx = get_mexico_now()
        delta = ahora_mx - fecha_mx
        return delta.total_seconds() < 86400  # 24 horas en segundos

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

    id           = Column(Integer, primary_key=True, autoincrement=True)
    municipio_id = Column(String,  nullable=False)  # ej. "030"
    nombre       = Column(String,  nullable=False)
    entidad_id   = Column(Integer, ForeignKey("cne_entidades.id"), nullable=False)

    entidad = relationship("EntidadFederativa", back_populates="municipios")

    __table_args__ = (
        UniqueConstraint("municipio_id", "entidad_id", name="uq_municipio_entidad"),
    )


class Localidad(Base):
    """Catálogo de localidades por municipio (CNE)."""
    __tablename__ = "cne_localidades"
    __table_args__ = (
        UniqueConstraint("localidad_id", "municipio_id", "entidad_id",
                         name="uq_localidad_municipio"),
        Index("ix_loc_ent_mun", "entidad_id", "municipio_id"),
    )

    # ── PK interna ─────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── IDs reales CNE (para armar URL de precios y joins) ─────
    localidad_id  = Column(Integer, nullable=False)  # ej. 289
    entidad_id    = Column(Integer, nullable=False)  # ej. 26
    municipio_id = Column(String,  nullable=False)  # ej. "030"

    # ── Nombre para UI ─────────────────────────────────────────
    nombre = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "localidad_id", "municipio_id", "entidad_id",
            name="uq_localidad_municipio"
        ),
    )

    def __repr__(self):
        return (
            f"<Localidad id={self.localidad_id} "
            f"nombre={self.nombre} "
            f"entidad={self.entidad_id} "
            f"municipio={self.municipio_id}>"
        )

    def api_params(self) -> dict:
        """Parámetros listos para la API de precios CNE."""
        return {
            "localidadId": self.localidad_id,
            "entidadId":   self.entidad_id,
            "municipioId": self.municipio_id,
        }

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
    fecha_extraccion = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


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
    
    def esta_vigente(self) -> bool:
        """
        Gas LP se actualiza semanalmente (cada sábado).
        Usamos la fecha de México para determinar vigencia.
        """
        fecha: datetime = cast(datetime, self.fecha_extraccion)
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        fecha_mx = to_mexico_tz(fecha)
        ahora_mx = get_mexico_now()
        
        # Obtener el último sábado en zona horaria de México
        hoy_mx = ahora_mx.date()
        dias_desde_sabado = (hoy_mx.weekday() - 5) % 7
        ultimo_sabado = ahora_mx.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=dias_desde_sabado)
        
        return fecha_mx >= ultimo_sabado


class Usuario(Base):
    """
    Usuario autenticado con Google (Fase 4). Nunca se almacenan contraseñas
    ni tokens de Google: solo la identidad estable `google_sub` (el claim `sub`
    del ID token, inmutable por cuenta) como PK.

    El `username` es OPCIONAL y distinto del `google_sub`; el usuario puede
    fijarlo/cambiarlo. Se guarda normalizado a minúsculas y con unicidad
    case-insensitive garantizada por la app (regex + denylist en el router).
    PII mínima: `email`, `nombre` y `foto_url` son opcionales (display/contacto).
    """
    __tablename__ = "usuarios"

    google_sub = Column(String, primary_key=True)

    email          = Column(String, nullable=True, index=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    username       = Column(String(30), nullable=True, unique=True)
    nombre         = Column(String, nullable=True)
    foto_url       = Column(String, nullable=True)

    creado_en      = Column(DateTime(timezone=True), default=get_mexico_now, nullable=False)
    actualizado_en = Column(DateTime(timezone=True), default=get_mexico_now,
                            onupdate=get_mexico_now, nullable=False)
    ultimo_login   = Column(DateTime(timezone=True), default=get_mexico_now, nullable=True)

    def __repr__(self):
        return f"<Usuario sub={self.google_sub} username={self.username}>"


class ChatHistorial(Base):
    """
    Conversaciones persistidas de usuarios con sesión (Fase 4). El contenido se
    consume/escribe hasta que exista el backend del chat (Fase 3). Sin sesión no
    se persiste nada.
    """
    __tablename__ = "chat_historial"
    __table_args__ = (
        Index("ix_chat_usuario_sesion", "google_sub", "sesion_id", "creado_en"),
    )

    id         = Column(Integer, primary_key=True, autoincrement=True)
    google_sub = Column(String, ForeignKey("usuarios.google_sub", ondelete="CASCADE"),
                        nullable=False, index=True)
    sesion_id  = Column(String, nullable=False)
    rol        = Column(String, nullable=False)          # "user" | "assistant"
    contenido  = Column(Text, nullable=False)
    metadatos  = Column(JSON, nullable=True)             # tool calls, contexto de municipio, etc.
    creado_en  = Column(DateTime(timezone=True), default=get_mexico_now, nullable=False)

    def __repr__(self):
        return f"<ChatHistorial sub={self.google_sub} rol={self.rol}>"