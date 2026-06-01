# SINA — Sistema de Información Nacional de Ahorro

<div align="center">

> Plataforma pública de consulta de precios de productos y servicios de primera necesidad en México.

[![Python](https://img.shields.io/badge/Python-3.12+-474848?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Podman](https://img.shields.io/badge/Podman-3.x+-892CA0?style=for-the-badge&logo=podman&logoColor=white)](https://podman.io/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=for-the-badge&logo=python&logoColor=white)](https://www.sqlalchemy.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.3+-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.35+-43B02A?style=for-the-badge&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-0.5+-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.ai/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.11+-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/es/docs/Web/HTML)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/es/docs/Web/JavaScript)
[![License](https://img.shields.io/badge/License-MIT-F7DF1E?style=for-the-badge&logo=opensource&logoColor=black)](LICENSE)

</div>

---

## 📋 Resumen

SINA es una plataforma **100% pública** que centraliza datos de precios de:
- ⛽ **Gasolina** (CRE)
- 🔥 **Gas LP** (CNE)
- 🛒 **Canasta básica / Supermercados** (PROFECO)
- 🏪 **Soriana** (Web scraping + DB-driven)

**Objetivo:** Empoderar al ciudadano con información clara para tomar mejores decisiones de compra y ahorro.

---

## 🚀 Características Principales

### ✅ Funcionalidad Actual (MVP)

| Módulo | Estado | Descripción |
|--------|--------|-------------|
| API Backend | ✅ Activo | FastAPI con SQLAlchemy ORM |
| Pipeline Gasolina | ✅ Activo | Scraping diario automático |
| Pipeline Gas LP | ✅ Activo | Scraping semanal (sábados) |
| Pipeline QQP | ✅ Activo | Actualización manual disponible |
| Pipeline Soriana | ✅ Activo | DB-driven scraping con PostgreSQL |
| Dashboard Gasolina | ✅ Activo | Mapa + tabla ranking |
| Dashboard Gas LP | ✅ Activo | Comparador por proveedor |
| Dashboard QQP | ✅ Activo | Tabla con filtros y mapa |
| Dashboard Soriana | ✅ Activo | Filtrado por departamento/categoría |
| Annotator ML | ✅ Activo | Extracción de datos de volantes |

### 🎨 Roadmap (Fases)

| Fase | Objetivo | Estado |
|------|----------|--------|
| FASE 1 | Estabilizar pipelines automáticos | 🟡 En progreso |
| FASE 2 | Migrar a React SPA + Liquid Glass UI | 🔴 Pendiente |
| FASE 3 | Vector DB + RAG para búsqueda semántica | 🔴 Pendiente |
| FASE 4 | Chatbot agéntico con Google OAuth | 🔴 Pendiente |
| FASE 5 | ML automatizado para volantes de supermercados | 🔴 Pendiente |

---

## 🏗️ Arquitectura

### Stack Tecnológico

```
┌───────────────────────────────────────────────────────────────────┐
│                         USUARIO                                   │
│  (Dashboard HTML/JS + API REST + Soriana Config)                 │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Python 3.12+)                   │
│  - Main app: sina/main.py                                         │
│  - ORM: SQLAlchemy + Repository Pattern                           │
│  - DB: PostgreSQL (pgvector)                                     │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────────────┐
│              Capas de Procesamiento                                │
│  - scraping/: Gasolina, Gas LP, QQP, Soriana                      │
│  - processing/: ML, OCR, LLM                                      │
│  - db/: Models + Repositories                                      │
│  - config/: Settings, Credentials, Paths                          │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────────────┐
│              Base de Datos (PostgreSQL + pgvector)                 │
│  - gasolineras (ubicaciones + precios)                            │
│  - gas_lp_precios (por proveedor/localidad)                        │
│  - qqp_precios (canasta básica PROFECO)                           │
│  - cne_entidades, cne_municipios, cne_localidades                  │
│  - catalogos_config (rutas Soriana activas)                       │
│  - supermercados (productos + precios)                            │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────────────┐
│              Infraestructura (Podman + WSL2)                       │
│  - PostgreSQL 16 + pgvector                                       │
│  - Podman Desktop (machine virtual habilitado)                    │
└───────────────────────────────────────────────────────────────────┘
```

### Flujos de Datos

#### Gasolina (Diario 6:00 AM)
```
CRE API → scrape_municipio() → transform_gas_prices() → 
upsert_precios() → Caché 24h → Dashboard
```

#### Gas LP (Sábados 8:00 AM)
```
CNE API → get_precios_gas_lp() → Caché semanal → 
Dashboard (comparador proveedores)
```

#### QQP / Supermercados (Bimensual/Manual)
```
PROFECO CSV → extract_qqp() → df_to_dict() → 
guardar_en_bulk() → Dashboard con mapa
```

#### Soriana (On-demand)
```
catalogos_config (DB) → obtener_rutas_activas() → 
scrape_por_ruta() → guardar_en_db() → Dashboard
```

---

## 📊 Base de Datos

### Tablas Principales

| Tabla | Propósito | Campos Clave |
|-------|-----------|--------------|
| `gasolineras` | Precios + ubicaciones | `lat`, `lng`, `nombre`, `tipo_combustible`, `precio` |
| `gas_lp_precios` | Precios por proveedor | `empresa`, `localidad`, `precio`, `vigente` |
| `qqp_precios` | Canasta básica PROFECO | `producto`, `marca`, `presentacion`, `precio`, `tienda` |
| `cne_entidades` | Estados MX | `id`, `nombre` |
| `cne_municipios` | Municipios | `id`, `nombre`, `entidad_id`, `municipio_id` |
| `cne_localidades` | Localidades | `id`, `nombre`, `municipio_id` |
| `catalogos_config` | Rutas Soriana activas | `tienda`, `departamento`, `categoria`, `url_path`, `prioridad` |
| `supermercados` | Productos + precios | `producto`, `precio`, `pid`, `tienda`, `departamento`, `categoria` |

### Schema de Ejemplo

```python
# gasolineras
{
  "id": 1,
  "nombre": "Pemex Ciudad",
  "entidad_id": 4,
  "municipio_id": 100,
  "localidad_id": 1000,
  "lat": 29.3000,
  "lng": -106.9000,
  "tipo_combustible": "regular",
  "precio": 22.50,
  "vigente": True,
  "fecha_actualizacion": "2026-05-12T06:00:00Z"
}

# catalogos_config (Soriana)
{
  "id": 1,
  "tienda": "Soriana",
  "departamento": "despensa",
  "categoria": "Arroz",
  "url_path": "/despensa/arroz-frijol-y-semillas/arroz/",
  "prioridad": 1,
  "ultima_extraccion": "2026-05-12T10:00:00Z",
  "activo": True,
  "fecha_registro": "2026-05-12T08:00:00Z"
}

# supermercados
{
  "id": 1,
  "producto": "Leche",
  "precio": 21.90,
  "pid": 12345,
  "tienda": "Soriana",
  "departamento": "lacteos-y-huevo",
  "categoria": "Lácteos",
  "subcategoria": None,
  "embedding": [0.1, 0.2, ...],
  "fecha_actualizacion": "2026-05-12T10:00:00Z"
}
```

---

## 🛠️ Instalación y Configuración

### Requisitos Previos

- Python 3.12+
- uv (package manager)
- Podman Desktop instalado
- WSL2 habilitado en Windows

### Instalación de Podman Desktop (si no está instalado)

1. **Habilitar máquina virtual:**
   ```powershell
   powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs"
   ```

2. **Ejecutar en PowerShell Admin:**
   ```powershell
   Dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   Dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```

3. **Reiniciar** la computadora

### Instalación

```bash
# Clonar proyecto
git clone https://github.com/angelmerino-pnd/sina.git
cd sina

# Instalar dependencias
uv sync

# Ejecutar Podman (cargar imagen PostgreSQL)
podman load -i postgres_image.tar  # Si tienes la imagen

# Iniciar PostgreSQL con Podman
podman-compose up -d

# Ejecutar scraper de ubicaciones (una vez)
uv run python -c "from sina.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"
```

### Variables de Entorno

Crear `.env` basado en `.env.example`:

```bash
cp .env.example .env
# editar .env con tus credenciales
```

### Estructura de Carpetas

```
sina/
├── compose.yaml                    # Podman Compose para PostgreSQL
├── notebooks/
│   └── soriana_03.py              # Script para extraer categorías Soriana
├── src/
│   └── sina/
│       ├── main.py                # FastAPI app + endpoints
│       ├── config/
│       │   ├── settings.py        # Configuración general
│       │   ├── credentials.py     # DB_URL, URLs externas
│       │   ├── paths.py           # Rutas de archivos
│       │   ├── canasta.py         # Estructura de canasta básica
│       │   └── ...
│       ├── db/
│       │   ├── models.py          # SQLAlchemy models (incl. CatalogoConfig)
│       │   ├── repository.py      # Repository Pattern
│       │   └── seeder.py          # Seed data
│       ├── scraping/
│       │   ├── gas.py             # Pipeline gasolina
│       │   ├── gas_lp.py          # Pipeline gas LP
│       │   ├── qqp.py             # Pipeline QQP
│       │   ├── soriana.py         # Pipeline Soriana (DB-driven)
│       │   ├── casa_ley.py        # Scraping volantes
│       │   └── ...
│       ├── processing/
│       │   ├── records.py         # Transformación de datos
│       │   ├── image_segmentation.py  # ML annotations
│       │   ├── ollama_ocr.py      # Extracción LLM
│       │   └── ...
│       └── ...
├── templates/                      # HTML templates (Jinja2)
├── static/
│   ├── css/
│   ├── js/
│   └── ...
├── datos/                          # Data storage
│   ├── gasolineras/
│   ├── casa_ley/
│   └── ...
├── notebooks/                      # Jupyter notebooks
├── pyproject.toml                 # Dependencies
├── .env.example                   # Template variables
├── .dockerignore                  # Docker ignore rules
└── README.md                      # This file
```

### Ejecución

```bash
# Servidor desarrollo
uvicorn sina.main:app --reload --host 0.0.0.0 --port 8000

# En producción (Gunicorn)
gunicorn sina.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Iniciar con Podman (PostgreSQL)
podman-compose up -d

# Ejecutar seeder para cargar datos iniciales
uv run python -m sina.db.seeder
```

---

## 🔌 Endpoints API

### Gasolina

| Método | Endpoint | Parámetros | Descripción |
|--------|----------|------------|-------------|
| GET | `/api/v1/gasolina` | `estado`, `municipio` | Obtener precios |
| POST | `/api/v1/update/gasolina` | `estado`, `municipio` | Actualizar precios |
| POST | `/api/v1/update/ubicacion/gasolineras` | `estado`, `municipio` | Actualizar ubicaciones |

### Gas LP

| Método | Endpoint | Parámetros | Descripción |
|--------|----------|------------|-------------|
| GET | `/api/v1/gas-lp` | `estado`, `municipio`, `localidad` | Obtener precios |
| GET | `/api/v1/gas-lp/localidades` | `estado`, `municipio` | Listar localidades |
| GET | `/api/v1/gas-lp/by-ids` | `entidad_id`, `municipio_id`, `localidad_id` | Obtener por IDs |

### QQP / Canasta Básica

| Método | Endpoint | Parámetros | Descripción |
|--------|----------|------------|-------------|
| POST | `/api/v1/update/qqp` | — | Actualizar datos QQP |
| GET | `/api/v1/qqp/catalogo` | — | Obtener catálogo disponible |
| GET | `/api/v1/qqp/canasta` | `estado`, `municipio` | Obtener canasta estructurada |

### Soriana

| Método | Endpoint | Parámetros | Descripción |
|--------|----------|------------|-------------|
| GET | `/api/v1/soriana/catalogo` | — | Obtener rutas activas desde DB |
| GET | `/api/v1/soriana/ruta/{id}` | `id` | Obtener ruta específica |
| POST | `/api/v1/soriana/update` | — | Actualizar última extracción |

### Annotator

| Método | Endpoint | Parámetros | Descripción |
|--------|----------|------------|-------------|
| POST | `/api/v1/annotator/annotate` | `supermarket`, `city`, `date`, `image_name`, `bboxes` | Guardar anotaciones |
| POST | `/api/v1/annotator/flyer` | `supermarket`, `city` | Descargar volante |
| POST | `/api/v1/annotator/extract` | `supermarket`, `city`, `date` | Extraer texto con LLM |
| GET | `/api/v1/annotator/status` | `supermarket`, `city`, `date` | Verificar estado |

---

## 📈 Caching Estratégico

### Políticas de Cache

| Categoría | Frecuencia | Trigger | Tiempo de vida |
|-----------|------------|---------|----------------|
| Gasolina | Diaria | Usuario busca + datos > 24h | 24 horas |
| Gas LP | Semanal | Usuario busca + datos > último sábado | 7 días |
| QQP | Bimensual | Manual o schedule | 14 días |
| Ubicaciones | Una vez | Scraping inicial | Indefinido |
| Soriana | On-demand | Cada scraping | 1 día (se actualiza en DB) |

### Regla General

```
Si el usuario busca un lugar y los datos están vigentes → servir de caché
Si están vencidos → llamar API gobierno → guardar en DB → responder
```

---

## 📝 Esquema de Datos

### Gasolineras

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean

class Gasolinera(Base):
    __tablename__ = 'gasolineras'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    entidad_id = Column(Integer)
    municipio_id = Column(Integer)
    localidad_id = Column(Integer)
    lat = Column(Float)
    lng = Column(Float)
    tipo_combustible = Column(String)  # regular, premium, diesel
    precio = Column(Float)
    vigente = Column(Boolean, default=True)
    fecha_actualizacion = Column(DateTime)
```

### Gas LP

```python
from sqlalchemy import Column, Integer, String, Float, DateTime

class GasLPPrecio(Base):
    __tablename__ = 'gas_lp_precios'
    
    id = Column(Integer, primary_key=True)
    empresa = Column(String)
    entidad_id = Column(Integer)
    municipio_id = Column(Integer)
    localidad_id = Column(Integer)
    precio = Column(Float)
    vigente = Column(Boolean, default=True)
    fecha_actualizacion = Column(DateTime)
```

### QQP

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean

class QQPPrecio(Base):
    __tablename__ = 'qqp_precios'
    
    id = Column(Integer, primary_key=True)
    producto = Column(String)
    marca = Column(String)
    presentacion = Column(String)
    precio = Column(Float)
    tienda = Column(String)
    municipio_id = Column(Integer)
    vigente = Column(Boolean, default=True)
    fecha_actualizacion = Column(DateTime)
```

### Soriana (catalogos_config)

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean

class CatalogoConfig(Base):
    __tablename__ = 'catalogos_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tienda = Column(String, nullable=False, default="Soriana")
    departamento = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    url_path = Column(String, nullable=False)  # Ej: "/despensa/arroz-frijol-y-semillas/arroz/"
    activo = Column(Boolean, default=True)
    prioridad = Column(Integer, default=1)
    ultima_extraccion = Column(DateTime(timezone=True), nullable=True)
    fecha_registro = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

### Supermercados

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, mapped_column
from sqlalchemy.ext.declarative import mapped_column
from sqlalchemy.dialects.postgresql import VECTOR

class Supermercado(Base):
    __tablename__ = 'supermercados'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    producto = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    pid = Column(Integer, nullable=False, unique=True)
    tienda = Column(String, default="Soriana")
    departamento = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    subcategoria = Column(String, nullable=True)
    embedding = mapped_column(Vector(), nullable=True)
    fecha_actualizacion = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

## 🧪 Pruebas

### Unit Tests

```bash
# Ejecutar tests
pytest tests/ -v

# Test específico
pytest tests/test_gasolina.py -v
```

### Endpoints

```bash
# Gasolina
curl -X GET http://localhost:8000/api/v1/gasolina/sonora/hermosillo

# Gas LP
curl -X GET http://localhost:8000/api/v1/gas-lp/sonora/hermosillo/hermosillo

# QQP
curl -X POST http://localhost:8000/api/v1/update/qqp

# Soriana - Obtener rutas activas
curl -X GET http://localhost:8000/api/v1/soriana/catalogo
```

---

## 📊 Métricas de Éxito

### Criterios de Producción

- [x] Los pipelines funcionando en producción
- [x] Datos actualizándose automáticamente
- [x] UI responsive (mobile-first)
- [x] PostgreSQL con pgvector configurado
- [ ] Deployed en servidor público
- [ ] Dominio propio (sina.mx)
- [ ] Métricas: usuarios, consultas/día

### Nice to have

- [ ] Chatbot funcional
- [ ] Demo en vivo con datos reales
- [ ] Ahorro estimado mensual para usuario
- [ ] React SPA con Liquid Glass UI

---

## 🤝 Contribución

Las contribuciones son bienvenidas!

1. Fork el proyecto
2. Crea tu branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

---

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE)

---

## 🔗 Recursos

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Leaflet Maps](https://leafletjs.com/)
- [Ollama](https://ollama.ai/)
- [PROFECO QQP](https://www.profeco.gob.mx/)
- [CRE Gasolina](https://www.gob.mx/cre)
- [CNE Gas LP](https://www.cne.gob.mx/)
- [Podman Docs](https://podman.io/)
- [PostgreSQL + pgvector](https://pgvector.github.io/)

---

## 📦 Comandos Útiles

### Podman

```bash
# Iniciar PostgreSQL con compose
podman-compose up -d

# Ver logs
podman-compose logs -f

# Detener
podman-compose down

# Eliminar contenedores y volúmenes
podman-compose down -v

# Cargar imagen PostgreSQL
podman load -i postgres_image.tar

# Ejecutar comando en contenedor
podman exec sina_db psql -U sina_admin -d sina_db
```

### Soriana Script

```bash
# Extraer categorías de Soriana y generar config.json
python notebooks/soriana_03.py

# Ver rutas activas desde DB
python -c "from sina.db.repository import CatalogoRepository; repo = CatalogoRepository(db_url='postgresql://sina_admin:sina_password@localhost:5432/sina_db'); print(repo.obtener_rutas_activas())"
```

---

<div align="center">
© 2026 SINA — Sistema de Información Nacional de Ahorro
</div>
