from typing import Generic, TypeVar
from contextlib import contextmanager
from typing import cast as typing_cast
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import create_engine, insert, delete, select, event, distinct
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sina.db.models import (
    Base, PrecioQQP, PrecioGasolina,
    EntidadFederativa, Municipio, Localidad, GasLPPrecio,
)
from sina.config.credentials import DB_URL
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

T = TypeVar("T", bound=DeclarativeBase)

# ── Engine ÚNICO compartido por toda la app ─────────────────
_engine = create_engine(
    DB_URL,
    connect_args={"timeout": 30} if DB_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
if DB_URL.startswith("sqlite"):
    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")        # lectores y escritor coexisten
        cur.execute("PRAGMA synchronous=NORMAL")      # ~3x escritura, sigue siendo seguro
        cur.execute("PRAGMA busy_timeout=30000")      # 30s reintentos
        cur.execute("PRAGMA cache_size=-64000")       # 64 MB de cache
        cur.execute("PRAGMA temp_store=MEMORY")       # tablas temp en RAM
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

Base.metadata.create_all(_engine)
_SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


class BaseRepository(Generic[T]):
    """Repositorio genérico — todos comparten el mismo engine."""
    model: type[T]

    def __init__(self, db_url: str = DB_URL):
        # Mantenemos la firma por compatibilidad pero usamos el engine global
        self.engine = _engine
        self.Session = _SessionFactory

    def guardar_en_bulk(self, lista_datos: list[dict]) -> None:
        if not lista_datos:
            return
        with self.engine.begin() as conn:
            conn.execute(insert(self.model), lista_datos)

    def contar(self) -> int:
        with self.Session() as session:
            return session.query(self.model).count()

    def borrar_todo(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(delete(self.model))


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

    def obtener_canasta(self, estado: str, municipio: str) -> list[dict]:
        """
        Consulta productos de canasta básica para un estado-municipio.
        Sin filtro de cadenas — incluye todas las tiendas.
        Devuelve registros deduplicados.
        """
        from sina.config.canasta import todos_los_productos

        productos = todos_los_productos()

        with self.Session() as session:
            stmt = (
                select(self.model)
                .where(
                    self.model.estado == estado,
                    self.model.municipio == municipio,
                    self.model.producto.in_(productos),
                )
            )
            rows = session.execute(stmt).scalars().all()

            seen: set[tuple] = set()
            resultado: list[dict] = []

            for r in rows:
                key = (r.producto, r.presentacion, r.marca, r.cadena_comercial, r.precio)
                if key in seen:
                    continue
                seen.add(key)

                resultado.append({
                    "producto":         r.producto,
                    "presentacion":     r.presentacion,
                    "marca":            r.marca,
                    "categoria":        r.categoria,
                    "precio":           float(typing_cast(int, r.precio)),
                    "cadena_comercial": r.cadena_comercial,
                    "nombre_comercial": r.nombre_comercial,
                    "direccion":        r.direccion,
                    "estado":           r.estado,
                    "municipio":        r.municipio,
                })

            return resultado

    def obtener_catalogo_qqp(self) -> dict[str, list[str]]:
        """
        Devuelve { estado: [municipio, ...] } solo para combinaciones
        que realmente tienen datos de canasta básica.
        """
        from sina.config.canasta import todos_los_productos
        from sqlalchemy import distinct, func

        productos = todos_los_productos()

        with self.Session() as session:
            stmt = (
                select(
                    self.model.estado,
                    self.model.municipio,
                )
                .where(self.model.producto.in_(productos))
                .group_by(self.model.estado, self.model.municipio)
                .having(func.count(distinct(self.model.producto)) >= 5)
                .order_by(self.model.estado, self.model.municipio)
            )

            rows = session.execute(stmt).all()

            catalogo: dict[str, list[str]] = {}
            for estado, municipio in rows:
                catalogo.setdefault(estado, []).append(municipio)

            return catalogo
        
    def obtener_tiendas_canasta(self, estado: str, municipio: str) -> list[dict]:
        """
        Devuelve tiendas únicas con sus productos de canasta básica
        y coordenadas para el mapa.
        """
        from sina.config.canasta import todos_los_productos, producto_a_item

        productos = todos_los_productos()

        with self.Session() as session:
            stmt = (
                select(self.model)
                .where(
                    self.model.estado == estado,
                    self.model.municipio == municipio,
                    self.model.producto.in_(productos),
                )
            )
            rows = session.execute(stmt).scalars().all()

            tiendas_map: dict[str, dict] = {}

            for r in rows:
                # Saltar registros sin coordenadas
                if not r.latitud or not r.longitud:
                    continue
                if not r.nombre_comercial:
                    continue

                try:
                    lat = float(r.latitud)
                    lng = float(r.longitud)
                except (ValueError, TypeError):
                    continue

                # Saltar coordenadas inválidas
                if lat == 0 and lng == 0:
                    continue

                key = r.nombre_comercial.strip()
                item = producto_a_item(r.producto)
                if item is None:
                    continue

                if key not in tiendas_map:
                    tiendas_map[key] = {
                        "nombre":    r.nombre_comercial,
                        "cadena":    r.cadena_comercial,
                        "direccion": r.direccion or "",
                        "lat":       lat,
                        "lng":       lng,
                        "items":     {},
                    }

                # Guardar precio más bajo por item en esta tienda
                existing = tiendas_map[key]["items"].get(item)
                precio = float(r.precio) if r.precio else 0
                if existing is None or precio < existing["precio"]:
                    tiendas_map[key]["items"][item] = {
                        "precio": precio,
                        "marca":  r.marca or "",
                        "presentacion": r.presentacion or "",
                    }

            # Convertir a lista
            resultado = []
            for t in tiendas_map.values():
                resultado.append({
                    "nombre":    t["nombre"],
                    "cadena":    t["cadena"],
                    "direccion": t["direccion"],
                    "lat":       t["lat"],
                    "lng":       t["lng"],
                    "n_items":   len(t["items"]),
                    "items":     t["items"],
                })

            return resultado

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
        if not registros:
            return
        rows = [
            {
                "numero":    r["permiso"],
                "estado":    r["estado"],
                "municipio": r["municipio"],
                "latitud":   r["latitud"],
                "longitud":  r["longitud"],
            }
            for r in registros
        ]
        base = sqlite_insert(self.model)
        stmt = base.values(rows).on_conflict_do_update(
            index_elements=["numero"],
            set_={
                "latitud":  base.excluded.latitud,
                "longitud": base.excluded.longitud,
            },
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def upsert_precios(self, registros: list[dict]):
        if not registros:
            return
        rows = [
            {
                "numero":         r["numero"],
                "estado":         r["estado"],
                "municipio":      r["municipio"],
                "nombre":         r["nombre"],
                "direccion":      r["direccion"],
                "magna":          r["magna"],
                "premium":        r["premium"],
                "diesel":         r["diesel"],
                "fecha_registro": r["fecha_registro"],
            }
            for r in registros
        ]
        base = sqlite_insert(self.model)
        stmt = base.values(rows).on_conflict_do_update(
            index_elements=["numero"],
            set_={
                "nombre":         base.excluded.nombre,
                "direccion":      base.excluded.direccion,
                "magna":          base.excluded.magna,
                "premium":        base.excluded.premium,
                "diesel":         base.excluded.diesel,
                "fecha_registro": base.excluded.fecha_registro,
            },
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def municipios_con_coordenadas(self) -> set[tuple[str, str]]:
        """
        UNA query — todos los (estado, municipio) que ya tienen lat/lng.
        Reemplaza N llamadas a municipio_ya_scrapeado().
        """
        with self.Session() as session:
            rows = session.execute(
                select(self.model.estado, self.model.municipio)
                .where(self.model.latitud.is_not(None))
                .distinct()
            ).all()
        return {(e, m) for e, m in rows}

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
        if not registros:
            return
        base = sqlite_insert(self.model)
        stmt = base.values(registros).on_conflict_do_update(
            index_elements=[
                "entidad_id", "municipio_id", "localidad_id",
                "numero_permiso", "tipo", "capacidad_recipiente",
            ],
            set_={
                "precio":           base.excluded.precio,
                "marca_comercial":  base.excluded.marca_comercial,
                "fecha_extraccion": base.excluded.fecha_extraccion,
            },
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

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
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()