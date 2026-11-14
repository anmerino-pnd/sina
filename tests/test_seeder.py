"""Pruebas para los archivos semilla (datos/seeds/) y las funciones de sina.db.seeder."""
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from sina.config.paths import (
    CATALOGO_MUNICIPIOS_PATH,
    LOCALIDADES_PARQUET_PATH,
    UBICACIONES_GASOLINERAS_PARQUET_PATH,
)
from sina.db.models import (
    Base,
    CatalogoConfig,
    EntidadFederativa,
    Localidad,
    Municipio,
    PrecioGasolina,
)
from sina.db.seeder import (
    seed_catalogo_localidades,
    seed_catalogo_municipios,
    seed_catalogos,
    seed_ubicaciones_gasolineras,
)


def test_archivos_seeds_existen_y_tienen_esquema_valido():
    assert CATALOGO_MUNICIPIOS_PATH.exists(), "Falta catalogo_municipios.json en datos/seeds/"
    assert LOCALIDADES_PARQUET_PATH.exists(), "Falta cne_localidades.parquet en datos/seeds/"
    assert UBICACIONES_GASOLINERAS_PARQUET_PATH.exists(), "Falta ubicaciones_gasolineras.parquet en datos/seeds/"

    meta_loc = pq.read_metadata(LOCALIDADES_PARQUET_PATH)
    assert meta_loc.num_rows == 297_878
    schema_loc = pq.read_schema(LOCALIDADES_PARQUET_PATH)
    assert set(schema_loc.names) >= {"entidad_id", "municipio_id", "localidad_id", "nombre"}

    meta_gas = pq.read_metadata(UBICACIONES_GASOLINERAS_PARQUET_PATH)
    assert meta_gas.num_rows == 11_023
    schema_gas = pq.read_schema(UBICACIONES_GASOLINERAS_PARQUET_PATH)
    assert set(schema_gas.names) >= {"numero", "estado", "municipio", "latitud", "longitud"}


def test_seeder_idempotente_y_preserva_precios(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    # Parquets reducidos en tmp_path para probar el flujo completo en milisegundos
    loc_parquet = tmp_path / "localidades.parquet"
    pq.write_table(
        pa.Table.from_pylist([
            {"entidad_id": 26, "municipio_id": "030", "localidad_id": 289, "nombre": "Hermosillo"},
            {"entidad_id": 26, "municipio_id": "030", "localidad_id": 664, "nombre": "20 de Noviembre"},
        ]),
        loc_parquet,
    )

    gas_parquet = tmp_path / "gasolineras.parquet"
    pq.write_table(
        pa.Table.from_pylist([
            {
                "numero": "PL/10156/EXP/ES/2015",
                "estado": "sonora",
                "municipio": "hermosillo",
                "latitud": 29.17866,
                "longitud": -110.8879,
            },
            {
                "numero": "PL/10244/EXP/ES/2015",
                "estado": "sonora",
                "municipio": "hermosillo",
                "latitud": 29.05614,
                "longitud": -111.0181,
            },
        ]),
        gas_parquet,
    )

    with SessionLocal() as session:
        # 1a corrida
        r_mun_1 = seed_catalogo_municipios(session)
        assert r_mun_1["entidades"] == 32
        assert r_mun_1["municipios"] == 2476

        r_loc_1 = seed_catalogo_localidades(session, parquet_path=loc_parquet)
        assert r_loc_1["localidades_procesadas"] == 2

        # Pre-cargar una estación con precio de CRE pero sin coordenadas
        session.add(
            PrecioGasolina(
                numero="PL/10156/EXP/ES/2015",
                estado="sonora",
                municipio="hermosillo",
                nombre="ESTACION PRUEBA",
                magna=23.99,
            )
        )
        session.commit()

        r_gas_1 = seed_ubicaciones_gasolineras(session, parquet_path=gas_parquet)
        assert r_gas_1["gasolineras_ubicaciones"] == 2

        r_cat_1 = seed_catalogos(session)
        assert sum(r_cat_1.values()) > 0

        # Verificar que el upsert de coordenadas conservó el precio existente
        est = session.get(PrecioGasolina, "PL/10156/EXP/ES/2015")
        assert est is not None
        assert est.magna == pytest.approx(23.99)
        assert est.latitud == pytest.approx(29.17866)
        assert est.longitud == pytest.approx(-110.8879)

        # 2a corrida (idempotencia)
        r_mun_2 = seed_catalogo_municipios(session)
        assert r_mun_2 == {"entidades": 0, "municipios": 0}

        r_loc_2 = seed_catalogo_localidades(session, parquet_path=loc_parquet)
        assert r_loc_2["localidades_procesadas"] == 2
        assert session.query(Localidad).count() == 2

        r_cat_2 = seed_catalogos(session)
        assert sum(r_cat_2.values()) == 0
        assert session.query(CatalogoConfig).count() == sum(r_cat_1.values())

    engine.dispose()
