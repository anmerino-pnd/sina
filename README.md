# SINA — Sistema de Información Nacional de Ahorro

<div align="center">

> Plataforma pública de consulta de precios de productos y servicios de primera necesidad en México.

[![Python](https://img.shields.io/badge/Python-3.12+-474848?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.10+-61DAFE?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3.x+-0039DB?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-F7DF1E?style=for-the-badge&logo=opensource&logoColor=black)](LICENSE)

</div>

---

## 📋 Resumen

SINA es una plataforma **100% pública** que centraliza datos de precios de:
- ⛽ **Gasolina** (CRE)
- 🔥 **Gas LP** (CNE)
- 🛒 **Canasta básica / Supermercados** (PROFECO)

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
| Dashboard Gasolina | ✅ Activo | Mapa + tabla ranking |
| Dashboard Gas LP | ✅ Activo | Comparador por proveedor |
| Dashboard QQP | ✅ Activo | Tabla con filtros y mapa |
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
┌─────────────────────────────────────────────────────┐
│                    USUARIO                          │
│  (Dashboard HTML/JS + API REST)                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (Python 3.12+)         │
│  - Main app: sina/main.py                           │
│  - ORM: SQLAlchemy + Repository Pattern             │
│  - DB: SQLite (actual) / PostgreSQL (futuro)        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Capas de Procesamiento                  │
│  - scraping/: Gasolina, Gas LP, QQP, Casa Ley       │
│  - processing/: ML, OCR, LLM                        │
│  - db/: Models + Repositories                        │
│  - config/: Settings, Credentials, Paths            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Base de Datos                          │
│  - gasolineras (ubicaciones + precios)              │
│  - gas_lp_precios (por proveedor/localidad)         │
│  - qqp_precios (canasta básica PROFECO)             │
│  - cne_entidades, cne_municipios, cne_localidades   │
└─────────────────────────────────────────────────────┘
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

# qqp_precios
{
  "id": 1,
  "producto": "Leche",
  "marca": "Lala",
  "presentacion": "1L",
  "precio": 21.90,
  "tienda": "Soriana",
  "municipio": "Hermosillo",
  "vigente": True
}
```

---

## 🛠️ Instalación y Configuración

### Requisitos Previos

- Python 3.12+
- uv (package manager)

### Instalación

```bash
# Clonar proyecto
git clone https://github.com/angelmerino/sina.git
cd sina

# Instalar dependencias
uv sync

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
├── src/
│   └── sina/
│       ├── main.py              # FastAPI app + endpoints
│       ├── config/
│       │   ├── settings.py      # Configuración general
│       │   ├── credentials.py   # DB_URL, URLs externas
│       │   ├── paths.py         # Rutas de archivos
│       │   ├── canasta.py       # Estructura de canasta básica
│       │   └── ...
│       ├── db/
│       │   ├── models.py        # SQLAlchemy models
│       │   ├── repository.py     # Repository Pattern
│       │   └── seeder.py        # Seed data
│       ├── scraping/
│       │   ├── gas.py           # Pipeline gasolina
│       │   ├── gas_lp.py        # Pipeline gas LP
│       │   ├── qqp.py           # Pipeline QQP
│       │   ├── casa_ley.py      # Scraping volantes
│       │   └── ...
│       ├── processing/
│       │   ├── records.py       # Transformación de datos
│       │   ├── image_segmentation.py  # ML annotations
│       │   ├── ollama_ocr.py    # Extracción LLM
│       │   └── ...
│       └── ...
├── templates/                   # HTML templates (Jinja2)
├── static/
│   ├── css/
│   ├── js/
│   └── ...
├── datos/                       # Data storage
│   ├── gasolineras/
│   ├── casa_ley/
│   └── ...
├── notebooks/                   # Jupyter notebooks
├── pyproject.toml              # Dependencies
└── .env.example                # Template variables
```

### Ejecución

```bash
# Servidor desarrollo
uvicorn sina.main:app --reload --host 0.0.0.0 --port 8000

# En producción (Gunicorn)
gunicorn sina.main:app -w 4 -k uvicorn.workers.UvicornWorker
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

### Regla General

```
Si el usuario busca un lugar y los datos están vigentes → servir de caché
Si están vencidos → llamar API gobierno → guardar en DB → responder
```

---

## 🎯 Fases de Desarrollo

### FASE 1: Estabilización (Actual)

**Objetivo:** Que los 3 pipelines corran solos sin intervención manual.

- [x] Scrapers funcionales
- [ ] **Pending:** Schedule automático (APScheduler)
- [ ] **Pending:** Logs unificados
- [ ] **Pending:** Health check endpoint

**Schedule propuesto:**
- Gasolina: Diario 6:00 AM
- Gas LP: Sábados 8:00 AM
- QQP: 1ro y 15 de cada mes

### FASE 2: React SPA + Liquid Glass UI

**Objetivo:** Migrar a React moderno con diseño Glassmorphism.

- [ ] Setup Vite + React + React Router
- [ ] Tailwind CSS + Liquid Glass components
- [ ] Migrar dashboards actuales
- [ ] Mapa Leaflet con marcadores
- [ ] Responsive mobile-first

### FASE 3: Vector DB + RAG

**Objetivo:** Preparar infraestructura para búsqueda semántica.

- [ ] pgvector o ChromaDB
- [ ] Vectorizar entidades (gasolineras, proveedores, productos)
- [ ] Endpoints de búsqueda vectorial

### FASE 4: Chatbot Agéntico

**Objetivo:** Asistente conversacional con Google OAuth.

- [ ] Router de intenciones (LLM)
- [ ] Tools para consultas específicas
- [ ] Google OAuth 2.0
- [ ] Historial de chat guardado

### FASE 5: ML Pipeline Automatizado

**Objetivo:** Automatizar extracción de volantes de supermercados.

- [ ] Roboflow training
- [ ] Object detection para zonas
- [ ] Pipeline completo sin anotación manual

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
```

---

## 📊 Métricas de Éxito

### Criterios de Producción

- [ ] Los 3 dashboards funcionando en SPA
- [ ] Datos actualizándose automáticamente
- [ ] UI responsive (mobile-first)
- [ ] Deployed en servidor público
- [ ] Dominio propio (sina.mx)
- [ ] Métricas: usuarios, consultas/día

### Nice to have

- [ ] Chatbot funcional
- [ ] Demo en vivo con datos reales
- [ ] Ahorro estimado mensual para usuario

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

---

<div align="center">
© 2026 SINA — Sistema de Información Nacional de Ahorro
</div>
