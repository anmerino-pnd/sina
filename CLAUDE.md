# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SINA (Sistema de Información Nacional de Ahorro) is a FastAPI app that aggregates Mexican
consumer prices — fuel (CRE), LP gas (CNE), and supermarket products (Soriana / Del Sol /
Benavides / Farmacias Guadalajara; Casa Ley flyers as a secondary track) — into one database
and serves dashboards + a REST API. The codebase is in Spanish: identifiers and methods use
Spanish verbs (`obtener_*`, `guardar_*`, `upsert_precios`, `necesita_actualizacion`). Match
that convention when adding code.

## Commands

Package manager is **uv** (Python ≥ 3.12). Prefix Python commands with `uv run`.

```bash
uv sync                                          # install deps
uv run uvicorn sina.main:app --reload            # dev server on :8000
uv run python -m sina.db.seeder                  # seed entidades/municipios/localidades + supermarket route catalogs (Soriana/Del Sol/Benavides/Guadalajara)
podman-compose up -d                             # start PostgreSQL 16 + pgvector (compose.yaml)
```

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
QQP endpoints are deprecated/removed; active API surfaces are gasolina, gas-lp, and
annotator.

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
  - `interfaces.py` — `BrowserConfig` dataclass shared by the browser-based scrapers.
- The catalog tree for each store is (re)generated by ad-hoc scripts in `notebooks/`
  (`woolworth_01.py` → Del Sol, `benavides_01.py`, `guadalajara_01.py`); `*_02.py` are the
  matching product-extraction prototypes. Product upserts dedupe by `pid` globally, so
  overlapping categories/stores never create duplicate rows.
- `scheduler.py` also has an **opt-in** weekly supermarket scraping job
  (`refrescar_supermercados`, Sun 04:00 MX), gated by `ENABLE_SUPERMERCADOS_SCRAPING` (off by
  default — it's heavy and must not run in a multi-instance web process).

**ML / annotation:**
- `annotator/image_segmentation.py` — flyer bounding-box annotations → crops; `records.py` —
  dataframe→dict transforms.
- `ollama/extract_flyer_text.py` — LLM/OCR extraction (imported defensively in `main.py`;
  becomes `None` if its deps are missing, so guard for that).
- `embedder/` — sentence/Qwen embeddings feeding the pgvector column.

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

Scraped flyer/image artifacts live under `datos/<supermarket>/<city>/<date>/` and are
served at `/datos`.
