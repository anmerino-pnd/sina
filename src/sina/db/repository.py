# src/sina/db/repository.py
from typing import Generic, TypeVar
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import create_engine, insert, delete, select
from sina.db.models import Base, PrecioQQP, PrecioGasolina
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """Repositorio genérico reutilizable para cualquier modelo SQLAlchemy."""

    model: type[T] 

    def __init__(self, db_url: str = "sqlite:///datos/db/sina_data.db"):
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