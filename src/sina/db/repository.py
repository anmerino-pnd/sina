# src/sina/db/repository.py
from typing import Generic, TypeVar
from sqlalchemy import create_engine, insert, delete
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.sina.db.models import Base, PrecioQQP, PrecioGasolina

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