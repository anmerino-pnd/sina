# src/sina/db/repository.py
from typing import Generic, TypeVar
from contextlib import contextmanager
from typing import cast as typing_cast
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import create_engine, insert, delete, select
from sina.db.models import  (
    Base, PrecioQQP, PrecioGasolina,
    EntidadFederativa, Municipio, Localidad, GasLPPrecio  
)
from sina.config.credentials import DB_URL
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """Repositorio genérico reutilizable para cualquier modelo SQLAlchemy."""

    model: type[T] 

    def __init__(self, db_url: str = DB_URL):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def guardar_en_bulk(self, lista_datos: list[dict]) -> None:
        if not lista_datos:
            print("No hay datos para insertar.")
            return

        try:
            with self.engine.begin() as conn:
                conn.execute(insert(self.model), lista_datos)
            print(f"[{self.model.__tablename__}] {len(lista_datos):,} registros guardados.")
        except Exception as e:
            print(f"[{self.model.__tablename__}] Error al guardar: {e}")
            raise

    def contar(self) -> int:
        """Cuenta los registros en la tabla."""
        with self.Session() as session:
            return session.query(self.model).count()

    def borrar_todo(self) -> None:
        """Borra todos los registros de la tabla. Úsalo con cuidado."""
        with self.engine.begin() as conn:
            conn.execute(delete(self.model))
        print(f"[{self.model.__tablename__}] Tabla vaciada.")


class QQPRepository(BaseRepository[PrecioQQP]):
    model = PrecioQQP

    def obtener_por_municipio(self, estado: str, municipio: str) -> list[dict]:
        """Consulta precios por estado y municipio."""
        with self.Session() as session:
            stmt = select(self.model).where(
                self.model.estado    == estado,
                self.model.municipio == municipio
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "producto"        : r.producto,
                    "presentacion"    : r.presentacion,
                    "marca"           : r.marca,
                    "categoria"       : r.categoria,
                    "precio"          : r.precio,
                    "fecha_registro"  : r.fecha_registro,
                    "cadena_comercial": r.cadena_comercial,
                    "nombre_comercial": r.nombre_comercial,
                    "direccion"       : r.direccion,
                    "estado"          : r.estado,
                    "municipio"       : r.municipio,
                    "latitud"         : r.latitud,
                    "longitud"        : r.longitud,
                }
                for r in rows
            ]

class GasolinaRepository(BaseRepository[PrecioGasolina]):
    model = PrecioGasolina

    def obtener_por_municipio(self, estado: str, municipio: str) -> list[dict]:
        """Consulta gasolineras por estado y municipio."""
        with self.Session() as session:
            stmt = select(self.model).where(
                self.model.estado    == estado.lower(),
                self.model.municipio == municipio.lower()
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "numero"   : r.numero,
                    "nombre"   : r.nombre,
                    "direccion": r.direccion,
                    "magna"    : r.magna,
                    "premium"  : r.premium,
                    "diesel"   : r.diesel,
                    "latitud"  : r.latitud,
                    "longitud" : r.longitud,
                    "fecha_extraccion": r.fecha_registro,
                }
                for r in rows
            ]
    def upsert_ubicaciones(self, registros: list[dict]):
        """
        Fase 1: Inserta ubicaciones. Si el numero ya existe, actualiza lat/lng.
        """
        with self.Session() as session:
            for r in registros:
                stmt = sqlite_insert(self.model).values(
                    numero    = r["permiso"],
                    estado    = r["estado"],
                    municipio = r["municipio"],
                    latitud   = r["latitud"],
                    longitud  = r["longitud"],
                ).on_conflict_do_update(
                    index_elements=["numero"],
                    set_={
                        "latitud" : r["latitud"],
                        "longitud": r["longitud"],
                    }
                )
                session.execute(stmt)
            session.commit()

    def upsert_precios(self, registros: list[dict]):
        """
        Fase 2: Actualiza precios. Respeta latitud/longitud ya existentes.
        """
        with self.Session() as session:
            for r in registros:
                stmt = sqlite_insert(self.model).values(
                    numero         = r["numero"],
                    estado         = r["estado"],
                    municipio      = r["municipio"],
                    nombre         = r["nombre"],
                    direccion      = r["direccion"],
                    magna          = r["magna"],
                    premium        = r["premium"],
                    diesel         = r["diesel"],
                    fecha_registro = r["fecha_registro"],
                ).on_conflict_do_update(
                    index_elements=["numero"],
                    set_={
                        "nombre"        : r["nombre"],
                        "direccion"     : r["direccion"],
                        "magna"         : r["magna"],
                        "premium"       : r["premium"],
                        "diesel"        : r["diesel"],
                        "fecha_registro": r["fecha_registro"],
                        # ✅ latitud y longitud NO están aquí → se preservan
                    }
                )
                session.execute(stmt)
            session.commit()

    def necesita_actualizacion(self, estado: str, municipio: str) -> bool:
        """
        True = no hay datos O tienen más de 24 horas.
        """
        with self.Session() as session:
            ultimo = (
                session.query(self.model)
                .filter_by(
                    estado=estado.lower(),
                    municipio=municipio.lower()
                )
                .order_by(self.model.fecha_registro.desc())
                .first()
            )
            if ultimo is None:
                return True
            return not ultimo.esta_vigente()

class EntidadFederativaRepository(BaseRepository[EntidadFederativa]):
    model = EntidadFederativa

class MunicipioRepository(BaseRepository[Municipio]):
    model = Municipio

    def obtener_catalogo(self) -> dict[str, list[str]]:
        """
        Devuelve { estado_nombre: [municipio_nombre, ...] }
        para el frontend. Todo en lowercase como el JSON anterior.
        """
        with self.Session() as session:
            entidades = session.query(EntidadFederativa).all()
            return {
                entidad.nombre.lower(): sorted([
                    m.nombre.lower() for m in entidad.municipios
                ])
                for entidad in entidades
            }

    def obtener_ids(self, estado: str, municipio: str) -> tuple[int, str] | None:
        """
        Dado estado y municipio como strings normalizados,
        devuelve (entidad_id, municipio_id_str) o None si no existe.
        """
        with self.Session() as session:
            entidad = (
                session.query(EntidadFederativa)
                .filter(EntidadFederativa.nombre.ilike(estado))
                .first()
            )
            if not entidad:
                return None

            municipio_row = (
                session.query(Municipio)
                .filter(
                    Municipio.entidad_id == entidad.id,
                    Municipio.nombre.ilike(municipio),
                )
                .first()
            )
            if not municipio_row:
                return None

            return (typing_cast(int, entidad.id), typing_cast(str, municipio_row.municipio_id))


    def obtener_nombres_validos(self) -> set[str]:
        """
        Devuelve todos los estados y municipios como strings
        lowercase. Reemplaza _build_municipios_validos().
        """
        with self.Session() as session:
            estados = {
                e.nombre.lower()
                for e in session.query(EntidadFederativa).all()
            }
            municipios = {
                m.nombre.lower()
                for m in session.query(Municipio).all()
            }
            return estados | municipios

class LocalidadRepository(BaseRepository[Localidad]):
    model = Localidad

class GasLPRepository(BaseRepository[GasLPPrecio]):
    model = GasLPPrecio

    def obtener_por_localidad(self, entidad_id: int, municipio_id: str, localidad_id: int) -> list[dict]:
        """Obtiene todos los precios de Gas LP para una localidad específica."""
        with self.Session() as session:
            stmt = select(self.model).where(
                self.model.entidad_id   == entidad_id,
                self.model.municipio_id == municipio_id,
                self.model.localidad_id == localidad_id,
            ).order_by(self.model.precio.asc())  # ← ordenado por precio (barato → caro)
            
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "numero_permiso":       r.numero_permiso,
                    "marca_comercial":      r.marca_comercial,
                    "tipo":                 r.tipo,
                    "capacidad_recipiente": r.capacidad_recipiente,
                    "precio":               r.precio,
                    "entidad_nombre":       r.entidad_nombre,
                    "municipio_nombre":     r.municipio_nombre,
                    "localidad_nombre":     r.localidad_nombre,
                    "fecha_extraccion":     r.fecha_extraccion,
                    "vigente":              r.esta_vigente(),
                }
                for r in rows
            ]

    def upsert_precios_gas_lp(self, registros: list[dict]):
        """
        Inserta o actualiza precios de Gas LP.
        Si ya existe (mismo permiso + tipo + capacidad + localidad), actualiza precio y fecha.
        """
        with self.Session() as session:
            for r in registros:
                stmt = sqlite_insert(self.model).values(**r).on_conflict_do_update(
                    index_elements=[
                        "entidad_id", "municipio_id", "localidad_id",
                        "numero_permiso", "tipo", "capacidad_recipiente"
                    ],
                    set_={
                        "precio":           r["precio"],
                        "marca_comercial":  r["marca_comercial"],
                        "fecha_extraccion": r["fecha_extraccion"],
                    }
                )
                session.execute(stmt)
            session.commit()
            print(f"[gas_lp_precios] {len(registros):,} registros actualizados.")

    def necesita_actualizacion(self, entidad_id: int, municipio_id: str, localidad_id: int, dias: int = 7) -> bool:
        """
        Verifica si los precios de esta localidad necesitan actualizarse.
        True = no hay datos O son más viejos que `dias` días.
        """
        with self.Session() as session:
            # Buscar el registro más reciente para esta localidad
            stmt = (
                select(self.model)
                .where(
                    self.model.entidad_id   == entidad_id,
                    self.model.municipio_id == municipio_id,
                    self.model.localidad_id == localidad_id,
                )
                .order_by(self.model.fecha_extraccion.desc())
                .limit(1)
            )
            
            ultimo = session.execute(stmt).scalars().first()
            
            if ultimo is None:
                return True  # No hay datos
            
            return not ultimo.esta_vigente()  # True si expiró

# ── Helper para obtener session (mantén compatibilidad) ────────
@contextmanager
def get_session():
    from sina.config.paths import DB
    engine = create_engine(f"sqlite:///{DB}/sina_data.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()