import logging
from typing import Generic, TypeVar
from contextlib import contextmanager
from typing import cast as typing_cast
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import (
    create_engine,
    insert,
    delete,
    select,
    event,
    text,
    update)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sina.db.models import (
    Base, PrecioGasolina,
    EntidadFederativa, Municipio, Localidad, GasLPPrecio,
    CatalogoConfig, Supermercado, Usuario, ChatHistorial,
)
from sina.config.credentials import DB_URL
from sina.config.timezone import get_mexico_now

log = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)

# ── Engine ÚNICO compartido por toda la app ─────────────────
# Pool afinado para Cloud SQL: mantener POCAS conexiones por instancia y
# escalar horizontalmente (más instancias) evita agotar `max_connections`.
# Parametrizable por entorno (DB_POOL_SIZE / DB_MAX_OVERFLOW).
import os as _os

_pool_kwargs: dict = {}
if not DB_URL.startswith("sqlite"):
    _pool_kwargs = {
        "pool_size":     int(_os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow":  int(_os.getenv("DB_MAX_OVERFLOW", "5")),
        "pool_timeout":  30,
        "pool_recycle":  1800,   # < idle timeout de Cloud SQL
    }

_engine = create_engine(
    DB_URL,
    connect_args={"timeout": 30} if DB_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    **_pool_kwargs,
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

# pgvector vive en PostgreSQL: la extensión debe existir antes de crear las
# tablas que usan la columna Vector (p. ej. `supermercados`).
if DB_URL.startswith("postgresql"):
    with _engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

Base.metadata.create_all(_engine)

# La búsqueda de productos usa ILIKE '%q%' (comodín inicial): sin índice trigram
# es un full-scan de `supermercados`. Solo PostgreSQL; SQLite (dev) se queda con
# el scan, aceptable a su escala.
if DB_URL.startswith("postgresql"):
    with _engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_supermercados_producto_trgm "
            "ON supermercados USING gin (producto gin_trgm_ops)"
        ))

_SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


def _dialect_insert(model):
    """
    INSERT con `on_conflict_do_update` según el dialecto del engine.
    El constructo de SQLite no compila bajo PostgreSQL (y viceversa), pero
    ambos comparten la API `on_conflict_do_update(index_elements=..., set_=...)`
    y `.excluded`, así que los upserts no cambian de forma.
    """
    if _engine.dialect.name == "postgresql":
        return pg_insert(model)
    return sqlite_insert(model)


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

    def _estado_cache(self, campo_fecha: str, evaluar_vigencia: bool = True) -> dict:
        """
        Última actualización y vigencia (para el health check), parametrizado
        por el campo de fecha del modelo. `evaluar_vigencia=False` deja
        `vigente` en None (sin regla de vigencia definida).
        """
        columna = getattr(self.model, campo_fecha)
        with self.Session() as session:
            ultimo = (
                session.query(self.model)
                .filter(columna.is_not(None))
                .order_by(columna.desc())
                .first()
            )
        if ultimo is None:
            return {
                "ultima_actualizacion": None,
                "vigente": False if evaluar_vigencia else None,
            }
        return {
            "ultima_actualizacion": getattr(ultimo, campo_fecha),
            "vigente": ultimo.esta_vigente() if evaluar_vigencia else None,
        }


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
        base = _dialect_insert(self.model)
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
        base = _dialect_insert(self.model)
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

    def ubicaciones_con_precios(self) -> list[tuple[str, str]]:
        """
        (estado, municipio) distintos que ya tienen al menos un precio cargado.
        Lo usa el scheduler para saber qué refrescar.
        """
        with self.Session() as session:
            rows = session.execute(
                select(self.model.estado, self.model.municipio)
                .where(self.model.fecha_registro.is_not(None))
                .distinct()
            ).all()
        return [(e, m) for e, m in rows]

    def estado_cache(self) -> dict:
        """Última actualización y vigencia (para el health check)."""
        return self._estado_cache("fecha_registro")

class EntidadFederativaRepository(BaseRepository[EntidadFederativa]):
    model = EntidadFederativa

class MunicipioRepository(BaseRepository[Municipio]):
    model = Municipio

    def obtener_catalogo(self) -> dict[str, list[str]]:
        """
        Devuelve { estado_nombre: [municipio_nombre, ...] }
        para el frontend. Todo en lowercase como el JSON anterior.
        UNA sola query con JOIN (antes: 1 + N por la relación lazy).
        """
        with self.Session() as session:
            rows = session.execute(
                select(EntidadFederativa.nombre, Municipio.nombre)
                .join(Municipio, Municipio.entidad_id == EntidadFederativa.id)
            ).all()
        catalogo: dict[str, list[str]] = {}
        for entidad_nombre, municipio_nombre in rows:
            catalogo.setdefault(entidad_nombre.lower(), []).append(municipio_nombre.lower())
        return {estado: sorted(municipios) for estado, municipios in catalogo.items()}

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
        base = _dialect_insert(self.model)
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

    def combinaciones_con_datos(self) -> list[dict]:
        """
        Combinaciones (entidad/municipio/localidad) distintas con datos en DB,
        incluyendo nombres. Lo usa el scheduler para saber qué refrescar.
        """
        with self.Session() as session:
            rows = session.execute(
                select(
                    self.model.entidad_id,
                    self.model.municipio_id,
                    self.model.localidad_id,
                    self.model.entidad_nombre,
                    self.model.municipio_nombre,
                    self.model.localidad_nombre,
                ).distinct()
            ).all()
        return [
            {
                "entidad_id": r.entidad_id,
                "municipio_id": r.municipio_id,
                "localidad_id": r.localidad_id,
                "entidad_nombre": r.entidad_nombre,
                "municipio_nombre": r.municipio_nombre,
                "localidad_nombre": r.localidad_nombre,
            }
            for r in rows
        ]

    def estado_cache(self) -> dict:
        """Última actualización y vigencia (para el health check)."""
        return self._estado_cache("fecha_extraccion")

# ── Repositorio para Catálogo de Rutas Soriana ─────────────────
class SupermercadoRepository(BaseRepository[Supermercado]):
    model = Supermercado

    @staticmethod
    def _normalizar_producto(p: dict, ahora: datetime) -> dict | None:
        """
        Convierte un producto de scraper (claves variables, p. ej. `pid_origen`)
        en un dict con exactamente las columnas del modelo. Devuelve None si el
        producto es inválido (sin pid, sin nombre o sin precio).
        """
        pid = p.get("pid", p.get("pid_origen"))
        try:
            pid = int(pid)
        except (ValueError, TypeError):
            return None

        nombre = " ".join(str(p.get("producto", "")).split()).strip()
        if not nombre:
            return None

        try:
            precio = float(p["precio"])
        except (KeyError, ValueError, TypeError):
            return None

        sub = p.get("subcategoria")
        return {
            "pid":          pid,
            "producto":     nombre,
            "precio":       precio,
            "tienda":       p.get("tienda") or "Soriana",
            "departamento": p.get("departamento") or "",
            "categoria":    p.get("categoria") or "",
            "subcategoria": sub if sub not in ("", None) else None,
            "fecha_actualizacion": ahora,
        }

    def upsert_productos(self, productos: list[dict]) -> int:
        """
        Inserta o actualiza productos en la tabla `supermercados`.

        Acepta los dicts tal como los producen los spiders (clave `pid_origen`),
        los normaliza a las columnas del modelo, deduplica por `pid` dentro del
        lote y, si `ENABLE_EMBEDDINGS` está activo (solo PostgreSQL), genera y
        guarda el embedding de cada producto.

        Returns:
            int: número de productos guardados/actualizados.
        """
        if not productos:
            return 0

        # Normalizar + dedup por pid (último gana) para no chocar en ON CONFLICT.
        ahora = get_mexico_now()
        filas_por_pid: dict[int, dict] = {}
        for p in productos:
            fila = self._normalizar_producto(p, ahora)
            if fila is not None:
                filas_por_pid[fila["pid"]] = fila
        filas = list(filas_por_pid.values())
        if not filas:
            return 0

        # Embeddings opcionales (gated por ENABLE_EMBEDDINGS; requiere pgvector).
        incluir_embedding = False
        if DB_URL.startswith("postgresql"):
            from sina.embedder.embeddings import get_embedding_service
            service = get_embedding_service()
            if service is not None:
                try:
                    vectores = service.vectorizar_productos(filas)
                    for fila, vec in zip(filas, vectores):
                        fila["embedding"] = vec
                    incluir_embedding = True
                except Exception as e:
                    log.error("Error generando embeddings de productos: %s", e)

        base = _dialect_insert(self.model)
        set_ = {
            "producto":            base.excluded.producto,
            "precio":              base.excluded.precio,
            "departamento":        base.excluded.departamento,
            "categoria":           base.excluded.categoria,
            "subcategoria":        base.excluded.subcategoria,
            "fecha_actualizacion": base.excluded.fecha_actualizacion,
        }
        if incluir_embedding:
            set_["embedding"] = base.excluded.embedding

        stmt = base.values(filas).on_conflict_do_update(
            index_elements=["pid"],
            set_=set_,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return len(filas)

    def buscar(
        self,
        q: str | None = None,
        tienda: str | None = None,
        departamento: str | None = None,
        categoria: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        """
        Busca productos con filtros duros (tienda/departamento/categoría).

        Si `q` viene y hay embeddings disponibles (PostgreSQL + ENABLE_EMBEDDINGS),
        ordena por similitud coseno sobre pgvector. Si no, cae a búsqueda de texto
        (ILIKE sobre el nombre) ordenada por precio ascendente.
        """
        limit = max(1, min(int(limit), 100))

        with self.Session() as session:
            stmt = select(self.model)
            if tienda:
                stmt = stmt.where(self.model.tienda.ilike(tienda))
            if departamento:
                stmt = stmt.where(self.model.departamento.ilike(departamento))
            if categoria:
                stmt = stmt.where(self.model.categoria.ilike(categoria))

            usar_vector = False
            if q:
                if DB_URL.startswith("postgresql"):
                    from sina.embedder.embeddings import get_embedding_service
                    service = get_embedding_service()
                    if service is not None:
                        try:
                            vector = service.vectorizar_consulta(q)
                            stmt = (
                                stmt.where(self.model.embedding.is_not(None))
                                .order_by(self.model.embedding.cosine_distance(vector))
                            )
                            usar_vector = True
                        except Exception as e:
                            log.error("Error en búsqueda vectorial, usando texto: %s", e)
                if not usar_vector:
                    stmt = stmt.where(self.model.producto.ilike(f"%{q}%")).order_by(
                        self.model.precio.asc()
                    )
            else:
                stmt = stmt.order_by(self.model.precio.asc())

            rows = session.execute(stmt.limit(limit)).scalars().all()
            return [
                {
                    "pid":                 r.pid,
                    "producto":            r.producto,
                    "precio":              r.precio,
                    "tienda":              r.tienda,
                    "departamento":        r.departamento,
                    "categoria":           r.categoria,
                    "subcategoria":        r.subcategoria,
                    "fecha_actualizacion": r.fecha_actualizacion,
                }
                for r in rows
            ]

    def estado_cache(self) -> dict:
        """
        Última actualización (para el health check). No hay regla de vigencia
        definida para supermercados todavía, así que `vigente` queda en None.
        """
        return self._estado_cache("fecha_actualizacion", evaluar_vigencia=False)


class CatalogoRepository(BaseRepository[CatalogoConfig]):
    model = CatalogoConfig

    def obtener_rutas_activas(self, tienda: str = "Soriana") -> list[dict]:
        """Obtiene todas las rutas activas ordenadas por prioridad."""
        with self.Session() as session:
            stmt = select(self.model).where(
                self.model.activo == True,
                self.model.tienda == tienda
            ).order_by(self.model.prioridad.asc())
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "tienda": r.tienda,
                    "departamento": r.departamento,
                    "categoria": r.categoria,
                    "url_path": r.url_path,
                    "prioridad": r.prioridad,
                    "ultima_extraccion": r.ultima_extraccion,
                }
                for r in rows
            ]

    def obtener_ruta_por_id(self, id: int) -> dict | None:
        """Obtiene una ruta específica por ID."""
        with self.Session() as session:
            row = session.query(self.model).filter(
                self.model.id == id,
                self.model.activo == True
            ).first()
            return dict(row) if row else None

    def contar_rutas_activas(self) -> int:
        """Contador de rutas activas."""
        with self.Session() as session:
            return session.query(self.model).filter(
                self.model.activo == True
            ).count()

    def actualizar_ultima_extraccion(self, id: int) -> None:
        """Actualiza la fecha de última extracción de una ruta."""
        with self.engine.begin() as conn:
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(
                    ultima_extraccion=datetime.now(timezone.utc)
                )
            )

            conn.execute(stmt)


def _usuario_a_dict(u: Usuario) -> dict:
    return {
        "user_id":        u.google_sub,
        "username":       u.username,
        "nombre":         u.nombre,
        "foto_url":       u.foto_url,
        "email":          u.email,
        "email_verified": u.email_verified,
        "needs_username": u.username is None,
    }


class UsuarioRepository(BaseRepository[Usuario]):
    model = Usuario

    def upsert_login(
        self,
        google_sub: str,
        email: str | None,
        email_verified: bool,
        nombre: str | None,
        foto_url: str | None,
    ) -> dict:
        """
        Get-or-create al iniciar sesión. Portable (no usa ON CONFLICT de un
        dialecto concreto): si el usuario existe, refresca atributos mutables
        y `ultimo_login`; si no, lo crea. La PK es `google_sub` (claim `sub`).
        Nunca se guardan tokens ni contraseñas.
        """
        with self.Session() as session:
            u = session.get(Usuario, google_sub)
            if u is None:
                u = Usuario(google_sub=google_sub)
                session.add(u)
            u.email          = email
            u.email_verified = email_verified
            u.nombre         = nombre
            u.foto_url       = foto_url
            u.ultimo_login   = get_mexico_now()
            session.commit()
            session.refresh(u)
            return _usuario_a_dict(u)

    def obtener_por_sub(self, google_sub: str) -> dict | None:
        with self.Session() as session:
            u = session.get(Usuario, google_sub)
            return _usuario_a_dict(u) if u else None

    def username_en_uso(self, username: str, excepto_sub: str) -> bool:
        """Unicidad case-insensitive; ignora al propio usuario."""
        with self.Session() as session:
            existe = (
                session.query(Usuario)
                .filter(
                    Usuario.username == username,
                    Usuario.google_sub != excepto_sub,
                )
                .first()
            )
            return existe is not None

    def fijar_username(self, google_sub: str, username: str) -> dict | None:
        with self.Session() as session:
            u = session.get(Usuario, google_sub)
            if u is None:
                return None
            u.username = username
            session.commit()
            session.refresh(u)
            return _usuario_a_dict(u)


class ChatHistorialRepository(BaseRepository[ChatHistorial]):
    model = ChatHistorial


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