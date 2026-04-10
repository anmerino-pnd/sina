# SINA — Context for Qwen Code

## Project Overview

**SINA** (Sistema de Información de Precios y Anotaciones) is a FastAPI-based web application for scraping, storing, and visualizing fuel prices (gasoline & LP gas) across Mexico. It also includes an image annotator for supermarket flyers with AI-powered text extraction via Ollama.

### Core Features

1. **Gasoline Price Tracker** — Fetches prices from the CRE (Comisión Reguladora de Energía) API, scrapes station coordinates from `gasolinamexico.com.mx`, and serves them via a web UI with 24-hour caching.
2. **LP Gas Price Tracker** — Uses the CNE (Comisión Nacional de Energía) API to retrieve LP gas prices for autotanques (bulk trucks) and recipientes (tanks), with weekly caching (expires Saturday).
3. **QQP Price Data** — Downloads and parses RAR/CSV archives from Profeco's open data portal for "Precios Quiosco de la Profeco."
4. **Flyer Annotator** — Web UI for drawing bounding boxes on supermarket flyer images, generating cropped regions, annotated images, and JSON labels. Supports AI text extraction via Ollama.

### Tech Stack

| Category | Technology |
|---|---|
| Backend | FastAPI (Python 3.12+) |
| Database | SQLite (local) or PostgreSQL (remote) via SQLAlchemy ORM |
| Scraping | Selenium, BeautifulSoup, requests |
| Image Processing | OpenCV (cropping, annotation rendering) |
| AI/LLM | Ollama (Qwen 3.5, cloud or local) |
| Frontend | Jinja2 templates + vanilla JS/CSS, Leaflet maps |
| Package Manager | `uv` (`pyproject.toml`, `uv.lock`) |

---

## Project Structure

```
sina/
├── src/sina/
│   ├── main.py                 # FastAPI app, all routes, lifespan
│   ├── chat.py                 # (empty)
│   ├── scraping/               # Data extraction modules
│   │   ├── casa_ley.py         # Selenium-based flyer downloader
│   │   ├── gas.py              # CRE API scraper + station location scraping
│   │   ├── gas_lp.py           # CNE API client for LP gas prices
│   │   └── qqp.py              # RAR/CSV parser for Profeco open data
│   ├── processing/
│   │   ├── image_segmentation.py  # Bbox crops, annotated images, JSON labels
│   │   └── records.py          # DataFrame-to-dict conversion for DB inserts
│   ├── db/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── repository.py       # Generic + specific repositories (upsert, caching)
│   │   └── seeder.py           # Seeds state/municipality catalog from JSON
│   ├── config/
│   │   ├── credentials.py      # Env vars → API URLs, DB connection string
│   │   ├── paths.py            # Path resolution (DATA, DB, TEMPLATES, STATIC)
│   │   ├── settings.py         # Classes JSON loader, filesystem tree builder
│   │   ├── classes.json        # Annotation classes → hex colors
│   │   └── prompt.py           # LLM prompt schema + JSON cleaner
│   └── ollama/
│       └── extract_flyer_text.py  # LLM-based text extraction from flyer crops
├── templates/                  # annotator.html, gasolina.html
├── static/                     # CSS + JS for frontend
│   ├── css/                    # annotator.css, gasolina.css
│   └── js/                     # annotator.js, gasolina.js
├── datos/                      # Data storage (gitignored: casa_ley, db)
├── notebooks/                  # Exploratory Jupyter notebooks
├── pyproject.toml              # Dependencies & entry point (sina = "sina:main")
└── .env.example                # Template for environment variables
```

---

## Database Models

| Model | Table | Purpose | Cache TTL |
|---|---|---|---|
| `PrecioGasolina` | `gasolineras` | Gas station prices + coordinates | 24 hours |
| `GasLPPrecio` | `gas_lp_precios` | LP gas prices by provider & locality | Weekly (Saturday) |
| `PrecioQQP` | `qqp_precios` | Profeco product prices | N/A (full replace) |
| `EntidadFederativa` | `cne_entidades` | Mexican states catalog | Static |
| `Municipio` | `cne_municipios` | Municipalities per state | Static |
| `Localidad` | `cne_localidades` | Localities per municipality | Static |

Key design patterns:
- **Upsert logic** via `sqlite_insert(...).on_conflict_do_update()` — preserves lat/lng when updating prices.
- **Cache invalidation** — `esta_vigente()` method on price models checks age against TTL.
- **Denormalization** — `GasLPPrecio` stores entity/municipality/locality names alongside IDs to avoid JOINs in frequent UI queries.

---

## API Endpoints

### Frontend
| Method | Route | Description |
|---|---|---|
| GET | `/sina/annotator` | Annotation UI for supermarket flyers |
| GET | `/sina/gasolina` | Gasoline price dashboard |

### Gasoline
| Method | Route | Description |
|---|---|---|
| GET | `/api/v1/gasolina` | Get prices by state/municipality (cached 24h) |
| POST | `/api/v1/update/gasolina` | Refresh prices from CRE API |
| POST | `/api/v1/update/ubicacion/gasolineras` | Scrape station coordinates |

### LP Gas
| Method | Route | Description |
|---|---|---|
| GET | `/api/v1/gas-lp` | Get LP gas prices by state/municipality/locality (cached weekly) |

### QQP (Profeco)
| Method | Route | Description |
|---|---|---|
| POST | `/api/v1/update/qqp` | Download & import latest QQP CSV data |

### Annotator
| Method | Route | Description |
|---|---|---|
| POST | `/api/v1/annotator/annotate` | Save bounding boxes, generate crops + annotated image |
| POST | `/api/v1/annotator/flyer` | Download flyer from supermarket (Casa Ley) |
| POST | `/api/v1/annotator/extract` | Extract text from crops using Ollama LLM |
| GET | `/api/v1/annotator/status` | Check if recortes/JSON exist for a date |

---

## Building and Running

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) package manager

### Setup
```bash
# Install dependencies
uv sync

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys and optional DB credentials
```

### Run the Server
```bash
uv run sina
# or equivalently:
uvicorn sina.main:app --reload
```

The app mounts:
- `/static` → `static/` directory
- `/datos` → `datos/` directory (serves stored images/data)

### Database Seeding
Before using the app, seed the state/municipality catalog:
```bash
uv run python -m sina.db.seeder
```

### Notebooks
Exploratory analysis lives in `notebooks/` — gas price maps (`mapa_diesel.html`, etc.), LP gas analysis, QQP parsing, and early extraction attempts.

---

## Configuration

### Environment Variables (see `.env.example`)
| Variable | Purpose |
|---|---|
| `QQP_DATOS_URL` | URL for Profeco QQP data |
| `DATOS_ABIERTOS_URL` | Base URL for open data RAR files |
| `CASA_LEY_URL` | Casa Ley flyer page URL |
| `GASOLINA_API_REST` | CRE gasoline prices API endpoint |
| `GASOLINERAS_UBI` | Gas station location scraper base URL |
| `CNE_LOCALIDADES_URL` | CNE localities catalog API |
| `CNE_PRECIOS_GAS_LP_URL` | CNE LP gas prices API |
| `OLLAMA_API_KEY` | API key for cloud Ollama |
| `GOOGLE_API_KEY` | (Unused currently) |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Optional PostgreSQL connection (falls back to SQLite) |

### DB Connection Strategy
The app auto-detects the database backend:
- If `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` are all set → **PostgreSQL**
- Otherwise → **SQLite** at `datos/db/sina_data.db`

---

## Development Conventions

### Code Style
- Python 3.12+ syntax (pattern matching, union types `X | None`, walrus operator `:=`)
- Type hints throughout — uses `cast()` from typing for ORM detachment scenarios
- Pydantic models for API request payloads (`AnnotationPayload`, `FlyerPayload`, `ExtractPayload`)
- Module-level logging via `logging.getLogger(__name__)`

### Architecture Patterns
- **Repository pattern** — `BaseRepository[T]` generic class with specialized subclasses per model
- **Caching** — Time-based staleness checks (`esta_vigente()`) before calling external APIs
- **Fallback behavior** — If external API fails, returns stale cached data with `fuente: "cache_vencido"`
- **Bulk inserts** — `guardar_en_bulk()` using SQLAlchemy `insert()` with list of dicts
- **Path resolution** — `find_project_root()` walks up from `__file__` to locate `pyproject.toml`

### Data Directory Layout (`datos/`)
```
datos/
├── db/                     # SQLite database (gitignored)
├── casa_ley/               # Casa Ley flyers (gitignored)
│   └── {city}/{date}/
│       ├── page_01.jpg     # Original images
│       ├── metadata.json   # Download metadata
│       ├── recortes/       # Cropped regions by class
│       ├── annotated/      # Images with drawn bounding boxes
│       ├── labels/         # JSON coordinate files
│       └── flyer_data.json # Extracted text from LLM
├── abarrey/                # Abarrey flyers (same structure)
└── gasolineras/            # Municipality catalog JSON
```

### Annotation Classes (`config/classes.json`)
| Class | Color (hex) |
|---|---|
| frutas_verduras | `#2ecc71` |
| carnes | `#e74c3c` |
| abarrotes | `#f1c40f` |
| lacteos | `#3498db` |
| ofertas_especiales | `#9b59b6` |
| banner | `#e67e22` |
| higiene | `#ff9ff3` |
| otros | `#95a5a6` |

---

## LLM Prompt Schema (`config/prompt.py`)

The system uses a structured prompt schema (`flyer_schema`) for extracting product data from supermarket flyers. The LLM (Qwen 3.5) is instructed to:

- Extract product name, brand, price, sale type, sale description, unit, and restrictions
- Identify validity dates (start/end) and store name
- Return ONLY JSON — no markdown wrapping, no explanations
- Use `null` for any field not visible in the image
- Classify promo mechanisms (3x2, 2x$X, descuento, etc.)

The `clean_response()` function strips markdown code fences from LLM output and parses JSON.

---

## Key File Descriptions

| File | Purpose |
|---|---|
| `src/sina/main.py` | FastAPI app entry point — all routes, lifespan (loads municipality catalog on startup), request validation |
| `src/sina/db/models.py` | SQLAlchemy ORM models with cache validity logic |
| `src/sina/db/repository.py` | Generic repository pattern + per-model upsert/query methods |
| `src/sina/scraping/gas.py` | CRE API client + `gasolinamexico.com.mx` station scraper |
| `src/sina/scraping/gas_lp.py` | CNE LP gas client with hierarchical location resolution |
| `src/sina/scraping/qqp.py` | RAR archive parser with encoding fixes for accented characters |
| `src/sina/scraping/casa_ley.py` | Selenium-based multi-page flyer downloader |
| `src/sina/processing/image_segmentation.py` | OpenCV-based bbox processing — crops, annotations, label JSON |
| `src/sina/config/credentials.py` | Environment variable loader, DB URL builder |
| `src/sina/config/paths.py` | Project root resolution, directory creation, locale setup (`es_MX.UTF-8`) |
| `src/sina/config/prompt.py` | LLM prompt schema for flyer extraction, JSON cleaner |
| `src/sina/db/seeder.py` | Populates state/municipality tables from JSON catalog |
| `src/sina/ollama/extract_flyer_text.py` | Batch-based LLM extraction from cropped images, merges into `flyer_data.json` |
| `templates/annotator.html` | Annotation UI: file tree, draw/pan/zoom tools, class selection, LLM extraction button, JSON modal |
| `templates/gasolina.html` | Gasoline dashboard: Leaflet map, autocomplete search, KPIs, ranking table, color-coded markers |
| `static/js/annotator.js` | Canvas drawing logic, bbox management, zoom controls |
| `static/js/gasolina.js` | Map rendering, autocomplete, ranking, nearby stations logic |

---

## Gitignored Files
- `.env` — Local secrets
- `datos/casa_ley/` — Downloaded flyer images
- `datos/db/` — SQLite database
- `__pycache__/`, `*.egg-info`, `chromedriver.exe`
