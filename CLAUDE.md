# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SINA (Sistema de Información Nacional de Ahorro) is a FastAPI app that aggregates Mexican
consumer prices — fuel (CRE), LP gas (CNE), and supermarket products (Soriana / Del Sol /
Benavides / Farmacias Guadalajara; Casa Ley / Abarrey flyers as a secondary track) — into one database
and serves dashboards + a REST API. The codebase is in Spanish: identifiers and methods use
Spanish verbs (`obtener_*`, `guardar_*`, `upsert_precios`, `necesita_actualizacion`). Match
that convention when adding code.

## Commands

Package manager is **uv** (Python ≥ 3.12). Prefix Python commands with `uv run`.

```bash
uv sync                                          # install deps
uv run uvicorn sina.main:app --reload            # dev server on :8000
uv run python -m sina.db.seeder                  # seed entidades/municipios/localidades + supermarket route catalogs (Soriana/Del Sol/Benavides/Guadalajara)
podman-compose up -d                             # start PostgreSQL 16 + pgvector + MongoDB (compose.yaml)
```

The chat agent (Fase 3) needs **Ollama** running with a tool-capable model
(`ollama pull qwen2.5:7b`) and `ENABLE_CHAT=1`. Chat history persists to **MongoDB** (from
compose); if Mongo is down the chat still answers, just without saving.

There is **no test suite** in the repo yet (the README's `pytest tests/` is aspirational —
no `tests/` directory exists). Verify changes by running the server and hitting endpoints,
e.g. `GET /api/v1/gasolina?estado=sonora&municipio=hermosillo`.

## Database selection (important gotcha)

`sina.config.credentials.get_db_url()` returns a **PostgreSQL** URL when all of
`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` env vars are set; otherwise it falls back to
**SQLite** at `datos/db/sina_data.db`. `DB_URL` is resolved **at import time**, and
`sina/db/repository.py` builds a single global engine and calls
`Base.metadata.create_all(_engine)` **on import** — so tables auto-create and the DB
target is locked in the moment any repository module is imported. Set `.env` (copy from
`.env.example`) before importing anything under `sina.db`.

## Architecture

**Entry point — `src/sina/main.py`:** the FastAPI `app`. On startup, a `lifespan` handler
loads the municipio catalog from the DB once into module-level globals
(`_municipios_validos`, `_catalogo_js`) used to validate `estado`/`municipio` query params.
Mounts `/static` and `/datos` (served files), renders Jinja2 templates from `templates/`.
QQP endpoints are deprecated/removed; active API surfaces are gasolina, gas-lp, supermercados,
chat (Fase 3), auth/users, and annotator.

**Data layer — `src/sina/db/`:**
- `models.py` — SQLAlchemy models. Notable: `PrecioGasolina` (`gasolineras`) uses the CRE
  permit string `numero` as PK and is filled in **two phases** (scraping fills
  `latitud/longitud`, the CRE API fills `magna/premium/diesel`); `GasLPPrecio` is
  intentionally **denormalized** (stores both IDs and names to avoid JOINs). `Supermercado`
  has a pgvector `embedding` column. Several models carry an `esta_vigente()` method
  encoding cache freshness (24h for gasolina, "since last Saturday" for gas LP), using
  Mexico-timezone helpers in `config/timezone.py`.
- `repository.py` — **all DB access goes through here** (centralized in commit `71f2ba9`).
  Generic `BaseRepository[T]` + one subclass per model (`GasolinaRepository`,
  `GasLPRepository`, `MunicipioRepository`, `CatalogoRepository`, etc.). All repos share
  the global `_engine`; the `db_url` constructor arg is kept only for signature
  compatibility and is ignored. Upserts use SQLite's `insert(...).on_conflict_do_update`.
- `seeder.py` — loads catalog/seed data. `seed_catalogo_tienda(session, tienda, config_path)`
  is a **generic** loader (top-level of each `*_config.json` = departamento, 2nd level =
  categoría, leaf = `{url_path, prioridad}`); `TIENDAS_CATALOGO` lists every store + its config
  file, and `seed_catalogos()` iterates it. Upserts are idempotent (dedup by
  tienda+departamento+categoría+url_path). Note: the config JSONs have **no top-level tienda
  wrapper** — the tienda name comes from `TIENDAS_CATALOGO`, not the file.

**Scrapers — `src/sina/scraping/`, organized by source:**
- `gobierno/cre_gasolina.py`, `gobierno/cne_gas_lp.py` — government APIs via `requests`.
  Use **on-demand caching**: `get_precios_*` checks `necesita_actualizacion()` /
  `esta_vigente()`; if stale, calls the gov API → `upsert_*` → returns. Otherwise serves
  from DB.
- Supermarket spiders are **DB-driven**: each reads its active routes from `catalogos_config`
  via `CatalogoRepository.obtener_rutas_activas(tienda=...)`, builds each URL as
  `<base_url> + route['url_path']`, scrapes, and `upsert`s to `supermercados`. The **base URL
  per store lives in `config/credentials.py`** (`soriana_base_url`, `delsol_base_url`,
  `benavides_base_url`, `guadalajara_base_url`, from `*_BASE_URL` env vars) — the config JSONs
  store only the `url_path`.
  - `supermercados/soriana_spider.py` (+ `soriana_helper.py`) — Salesforce Commerce Cloud,
    **playwright-stealth** (headless browser).
  - `supermercados/delsol_spider.py` (+ `delsol_helper.py`) — VTEX, **playwright-stealth async**.
  - `supermercados/benavides_spider.py` (+ `benavides_helper.py`) — Magento, `curl_cffi` +
    BeautifulSoup (server-rendered, no browser); paginates via `?p=N`.
  - `supermercados/guadalajara_spider.py` (+ `guadalajara_helper.py`) — Salesforce Commerce
    Cloud (same platform as Soriana) but server-rendered, so `curl_cffi` + BeautifulSoup;
    paginates via the SFCC "Show More" `Search-UpdateGrid?start=N&sz=20` fragment. Config
    covers only the **Super / Farmacia / Dermo** tabs (Ofertas excluded — it re-lists the same
    `pid`s and would overlap).
  - `supermercados/casaley_spider.py` — downloads flyer images via **Selenium** (Publitas).
  - `supermercados/abarrey_spider.py` — downloads flyer images from `ofertas.php`
    (server-rendered) via `curl_cffi` + BeautifulSoup; same output layout as Casa Ley
    (`page_NN.jpg` + `metadata.json`) plus `vigencia_texto` scraped from the page.
  - `interfaces.py` — `BrowserConfig` dataclass shared by the browser-based scrapers.
- The catalog tree for each store is (re)generated by ad-hoc scripts in `notebooks/`
  (`woolworth_01.py` → Del Sol, `benavides_01.py`, `guadalajara_01.py`); `*_02.py` are the
  matching product-extraction prototypes. Product upserts dedupe by `pid` globally, so
  overlapping categories/stores never create duplicate rows.
- `scheduler.py` also has an **opt-in** weekly supermarket scraping job
  (`refrescar_supermercados`, Sun 04:00 MX), gated by `ENABLE_SUPERMERCADOS_SCRAPING` (off by
  default — it's heavy and must not run in a multi-instance web process).

**Agente / Chat (Fase 3) — `src/sina/agent/`:** el asistente de ahorro.
- `llm/base.py` — `LLMProvider` (ABC) con `chat_stream`/`chat` + dataclasses `ToolCall`/`LLMUso`/`LLMDelta`.
  `llm/ollama_provider.py` (open-source local, tool-calling + streaming nativos de Ollama).
  `llm/factory.py` — `get_llm_provider()` perezoso, gated por `ENABLE_CHAT`, elegido por `LLM_PROVIDER`
  (mismo patrón que `embedder/embeddings.py`). Un patrocinador añade `gemini_provider.py` (subclase) y
  una rama en la fábrica; **las tools no cambian**.
- `tools/` — cada tool envuelve una consulta a los repos con su JSON Schema; `registry.construir_registro(ctx)`
  las crea **cerrando sobre un `ContextoConsulta`** (estado/municipio/localidad/lat/lng). El `lat/lng` se
  **inyecta** (el LLM nunca lo rellena). Tools: `buscar_gasolina` (precio o cercanía por haversine),
  `buscar_gas_lp`, `listar_localidades_gas_lp`, `buscar_producto`, `comparar_lista`, `armar_canasta`,
  `datos_disponibles`.
- `graph.py` — motor de grafo mínimo (estilo LangGraph, **sin** LangChain/LangGraph): nodos que pueden ser
  generadores (ceden eventos de streaming y `return` la actualización de estado), aristas fijas y condicionales.
- `agent.py` — `responder_stream(mensaje, contexto, historial, provider)` recorre el grafo `agente ↔ tools`
  (tope `LLM_MAX_ITERS`) cediendo eventos `paso`/`token`/`done`, y agrega **telemetría** por respuesta
  (tokens, tokens/seg, `tool_timings`, `phase_timings`). `geo.py` — haversine (R=6371, espeja `frontend/src/lib/geo.ts`).
- **Endpoint** `src/sina/api/chat.py`: `POST /api/v1/chat` es **SSE** (`text/event-stream`), sesión opcional
  (`require_csrf_si_sesion` en `deps.py`), rate-limited; **solo persiste al completar** el stream (pausa = no
  guarda). CRUD de conversaciones con paginación por puntero.

**MongoDB — `src/sina/db/mongo.py` + `chat_store.py` + `stores.py`:** `get_mongo_db()` perezoso
(devuelve `None` si Mongo no está → TODO lo de Mongo degrada suave, nunca es dependencia dura).
`ChatStore` implementa el **patrón bucket / lista ligada**: `conversaciones.cabeza_chunk_id` apunta
al chunk más reciente; cada `chat_chunks` guarda ≤`CHAT_CHUNK_SIZE` mensajes y un `anterior_id` al
chunk más viejo (paginación hacia atrás O(1)). Tope `CHAT_MAX_CONVERSACIONES` por usuario.
`stores.py` añade stores chicos con el mismo patrón degradable: `FlyerCiudadesStore` (colección
`flyer_ciudades`: ciudades añadidas desde la UI del anotador; el JSON `flyer_ciudades.json` queda
como **semilla** de solo lectura y el selector muestra semilla ∪ Mongo vía `ciudades_flyers()`) y
`RegistroJobsStore` (colección `registro_jobs`, TTL 90 días: auditoría de corridas del scheduler
vía el wrapper `_con_registro` — el monitor de flyers solo registra ticks con actividad; consulta
en `GET /api/v1/annotator/jobs`, admin). El **mapa de almacenamiento** completo (qué dato vive en
Postgres/Mongo/filesystem/git/navegador y por qué) está en `quarto/3_datos.qmd` §3.8. La tabla
Postgres `chat_historial` quedó **deprecada** (no se usa).

**ML / annotation (flyer pipeline, Fase 6):** descarga → **recorte por ZONAS** (bloques separados
por espacios en blanco, no por producto) → **VLM por zona** → verificación humana → Postgres.
- `annotator/zonas.py` — `detectar_zonas(image_path, tienda)`: pre-anotación de zonas con **CV
  clásico** (OpenCV), **dos modos elegidos por tienda** en `_PARAMS` (`"modo"`):
  - **paneles** (Casa Ley): sus flyers usan **paneles de color** sin pasillos blancos anchos, así
    que binarizar-y-cerrar fundía todo en un bloque; el enfoque es el **inverso**: detectar los
    **pasillos** (líneas claras largas, vía `open` morfológico con kernels alargados) y quedarse
    con los **paneles** entre ellos.
  - **bandas** (Abarrey): rejilla densa SIN pasillos continuos (los empaques interrumpen toda
    línea larga → el modo paneles da 0-2 zonas inútiles). Perfil de **blancura por fila**: los
    renglones mayormente claros separan; cada tramo no-blanco es una zona a lo ancho (≈ una
    fila/departamento, granularidad ideal para el VLM).
  Perilla **`fusion`** (0–0.05, UI: Ninguna/Media/Alta) que dilata-y-reagrupa cajas cercanas: 0
  para paneles de color; súbela si la detección sale fragmentada. Propuestas que el humano ajusta;
  clase única `zona`. YOLO (a futuro) reemplaza este paso.
- `annotator/image_segmentation.py` — `process_annotations` recorta las cajas → `recortes/`,
  guarda overlay + labels JSON **y export YOLO** (`labels_yolo/*.txt`, coords normalizadas =
  dataset para entrenar). Payloads `PreanotarPayload`/`PersistirPayload`. `resolver_ruta_flyer`
  guarda contra path traversal.
- `annotator/dataset.py` — `construir_dataset_yolo()` / `uv run python -m sina.annotator.dataset`:
  consolida todos los `labels_yolo/*.txt` de `datos/flyers/` en `datos/yolo_dataset/` formato
  Ultralytics (`images/labels × train/val` + `data.yaml`, split determinista por hash, nombres
  `tienda__ciudad__fecha__page_NN`). Decisión: YOLO **unificado** (todas las tiendas, mono-clase).
- `annotator/ciclo.py` — ciclo de vida por flyer inferido de artefactos en disco: descargado
  (`metadata.json`), anotado (`labels/`), extraído (`extraccion.json`, lo escribe `/extract`),
  persistido (`persistido.json`, lo escribe `/persistir`). Vigencia por **prioridad** (humano
  en persistido.json → parseada del scraping en metadata.json → desconocida) — **sin supuestos
  de calendario**: cada tienda dura y vence distinto. `resumen_pendientes()` alimenta
  `GET /annotator/pendientes` (panel "Folletos" de la UI, con precarga de vigencia en el modal)
  y el job `refrescar_flyers` de `scheduler.py` (opt-in `ENABLE_FLYERS_SCRAPING`, tick cada
  `FLYERS_INTERVALO_MIN`=20 min, barato si nada venció; descarga al vencer y limpia por hash si
  la tienda aún publica el flyer viejo para reintentar al siguiente tick).
- `vlm/` — **capa VLM abstracta** (espeja `agent/llm/`): `base.VLMProvider` (ABC),
  `ollama_vlm.OllamaVLMProvider` (visión local; `format=<json schema>` = salida estructurada real;
  `api_key` → nube), `factory.get_vlm_provider()` gated por `ENABLE_VLM`/`VLM_PROVIDER`/`VLM_MODEL`.
  `extraccion.extraer_recortes()` corre el VLM **por zona**, valida con **Pydantic + sanidad de
  precio** (`ProductoFlyer`) y devuelve productos por recorte. (El viejo `ollama/extract_flyer_text.py`
  quedó superado por `vlm/extraccion.py`.)
- Endpoints admin (`main.py`, `X-Admin-Key`): `POST /annotator/{flyer,preanotar,annotate,extract,
  persistir}`, `GET /annotator/{tree,status}`. `GET /sina/annotator` sirve solo el shell (la UI
  adjunta la key desde un campo). `persistir` → `SupermercadoRepository.upsert_flyer_productos`.
- `embedder/` — sentence/Qwen embeddings feeding the pgvector column.

**`supermercados` unifica scraping y flyer** (`db/models.py`): columna `fuente`
(`"scraping"`|`"flyer"`) + `vigencia_inicio/fin` + `marca`/`unidad`; `pid` es **nullable** (los
flyer no lo traen) y su dedup es por la clave compuesta `uq_super_flyer`
(`tienda, producto, fuente, vigencia_inicio`) vía `upsert_flyer_productos`. **Sin Alembic**: el
arranque de `repository.py` corre una migración idempotente (ALTER ... IF NOT EXISTS) solo en
PostgreSQL para alinear DBs existentes. `buscar(..., fuente=, solo_vigentes=)` filtra promos vigentes.

**Config — `src/sina/config/`:** `paths.py` (auto-detected `BASE_DIR`, `DATA`,
`TEMPLATES_DIR`, `STATIC_DIR`, `DB`, and the `*_CONFIG_PATH` for each store catalog),
`credentials.py` (env loading + `DB_URL`, `HEADERS`, per-store `*_base_url`), `settings.py`,
`canasta.py` (canasta-básica product mapping), the store route catalogs
(`soriana_config.json`, `delsol_config.json`, `benavides_config.json`,
`guadalajara_config.json`), `timezone.py` (Mexico-tz helpers used for cache vigency).

## Data flow (typical request)

```
GET /api/v1/gasolina?estado&municipio
  → _validar_ubicacion() (checks against catalog loaded at startup, resolves IDs)
  → get_precios_gasolina() → if cache fresh: return from DB
                           → else: CRE API → transform → repo.upsert_precios() → return
```

Scraped flyer/image artifacts live under `datos/flyers/<tienda>/<city>/<date>/` (flyer stores
—`casa_ley`, `abarrey`— are grouped under `datos/flyers/` so the annotator's store selector lists
only flyer sources, not `db/`/`gasolineras/`; `resolver_ruta_flyer` and the annotator tree are
rooted at `FLYERS_DATA`, images served at `/datos/flyers/...`) and are
served at `/datos`.
