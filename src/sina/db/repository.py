# src/sina/db/repository.py
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from src.sina.db.models import Base, PrecioQQP


class QQPRepository:
    def __init__(self, db_url: str = "sqlite:///qqp_data.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def guardar_en_bulk(self, lista_datos: list[dict]) -> None:
        """
        Recibe una lista de diccionarios y hace un bulk insert.
        Forma moderna compatible con SQLAlchemy 2.x
        """
        if not lista_datos:
            print("⚠️ No hay datos para insertar.")
            return

        with self.Session() as session:
            try:
                session.execute(insert(PrecioQQP), lista_datos)
                session.commit()
                print(f"✅ Se guardaron {len(lista_datos)} registros exitosamente.")
            except Exception as e:
                session.rollback()
                print(f"❌ Error al guardar en la base de datos: {e}")
                raise  # Re-lanza para no silenciar errores