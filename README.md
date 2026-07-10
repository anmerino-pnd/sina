# SINA — Sistema de Información Nacional de Ahorro

<div align="center">

_Sistema de Información Nacional de Ahorro — precios de primera necesidad para las familias mexicanas._

**Backend**

![Python](https://img.shields.io/badge/Python%203.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-2094F3?style=flat-square&logo=gunicorn&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white)
![APScheduler](https://img.shields.io/badge/APScheduler-4B8BBE?style=flat-square)

**Datos e IA**

![PostgreSQL](https://img.shields.io/badge/PostgreSQL%2016-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=flat-square&logo=ollama&logoColor=white)
![Hugging Face](https://img.shields.io/badge/Embeddings-FFD21E?style=flat-square&logo=huggingface&logoColor=black)

**Frontend**

![React](https://img.shields.io/badge/React%2019-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![React Router](https://img.shields.io/badge/React%20Router-CA4245?style=flat-square&logo=reactrouter&logoColor=white)
![TanStack Query](https://img.shields.io/badge/TanStack%20Query-FF4154?style=flat-square&logo=reactquery&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=flat-square&logo=leaflet&logoColor=white)

**Scraping**

![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4B8BBE?style=flat-square)
![curl_cffi](https://img.shields.io/badge/curl__cffi-073551?style=flat-square&logo=curl&logoColor=white)

**Auth, seguridad y tooling**

![Google OAuth](https://img.shields.io/badge/Google%20OAuth%202.0-4285F4?style=flat-square&logo=google&logoColor=white)
![slowapi](https://img.shields.io/badge/slowapi-rate--limit-555555?style=flat-square)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=flat-square&logo=uv&logoColor=white)
![Podman](https://img.shields.io/badge/Podman-892CA0?style=flat-square&logo=podman&logoColor=white)
![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

## Qué es

SINA centraliza precios de primera necesidad y los sirve en dashboards + una API REST:

- **Gasolina** — API de la CRE (Magna, Premium, Diésel por estación, con mapa).
- **Gas LP** — API de la CNE (precio por kilo por permisionario y localidad).
- **Supermercados** — scraping directo (Soriana, Del Sol, Farmacias Benavides y Farmacias
  Guadalajara; volantes de Casa Ley como track secundario) con búsqueda por texto y
  **semántica (pgvector)**.

**Misión:** empoderar a la familia mexicana con información clara y accesible para gastar menos.
El proyecto arranca en Hermosillo, Sonora, y crece por fases hacia el resto del país.

> La documentación de visión y alcance vive en [SPEC.md](SPEC.md). Las notas para trabajar el
> código están en [CLAUDE.md](CLAUDE.md).

---

## Estado actual

| Área                                                               | Estado                                           |
| ------------------------------------------------------------------- | ------------------------------------------------ |
| Backend FastAPI (gasolina, gas LP, supermercados, health)           | Funcional                                        |
| PostgreSQL 16 + pgvector (embeddings de productos)                  | Funcional (opt-in)                               |
| SPA React (Vite + Tailwind): landing, dashboards, modo oscuro       | Funcional                                        |
| Autenticación con Google + sesión segura (cookie httpOnly + CSRF) | Funcional (requiere configurar OAuth)            |
| Scheduler de actualizaciones (APScheduler)                          | Funcional                                        |
| Chat / asistente conversacional (Ollama + tools + grafo, SSE)       | Funcional (requiere Ollama; historial en MongoDB)  |
| Tests, CI/CD, contenedor de la app, despliegue GCP                  | **Pendiente**                              |

**Selección de base de datos (importante):** SINA usa **PostgreSQL** cuando están definidas las
variables `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`; si falta alguna, cae automáticamente a
**SQLite** local (`datos/db/sina_data.db`) como atajo de desarrollo. **pgvector y la búsqueda
semántica solo funcionan en PostgreSQL.** Gasolina funciona en ambos porque consulta la API de la
CRE bajo demanda; Gas LP y Supermercados necesitan PostgreSQL con datos sembrados/scrapeados.

---

## Requisitos

- **Python 3.12+** y **[uv](https://docs.astral.sh/uv/)** (gestor de paquetes).
- **Node.js 20+** y **npm** (para la SPA en `frontend/`).
- **Podman** + **podman-compose** (para PostgreSQL y MongoDB locales). En Windows, con WSL2.
- **[Ollama](https://ollama.com)** (opcional, solo para el chat) con un modelo con tool-calling
  (`ollama pull qwen2.5:7b`).

---

## Correr en local (flujo recomendado para experimentar)

La idea: **todo local con Podman**. Cuando haya un servidor patrocinado, solo se cambian valores
del `.env` (ver la siguiente sección) — no se toca código.

### 1. Preparar el proyecto

```bash
git clone https://github.com/angelmerino-pnd/sina.git
cd sina

uv sync                     # instala dependencias de Python
cp .env.example .env        # crea tu configuración local
```

El `.env.example` ya trae los valores de PostgreSQL que coinciden con `compose.yaml`
(`localhost:5432`, usuario `sina_admin`), así que para local no hace falta cambiar nada.

### 2. Levantar PostgreSQL + pgvector (y MongoDB) con Podman

```bash
podman-compose up -d        # arranca sina_db (pgvector/pgvector:pg16) y sina_mongo (mongo:7)
```

MongoDB solo se usa para el historial del chat (Fase 3). Si no lo levantas, todo lo demás
funciona; el chat responde pero sin guardar conversaciones.

### 3. Sembrar catálogos

```bash
uv run python -m sina.db.seeder
```

Esto carga entidades/municipios/**localidades** y los **catálogos de rutas de scraping** de
Soriana, Del Sol, Benavides y Farmacias Guadalajara. Es lo que habilita las localidades del
dashboard de **Gas LP** (sin seeder, esa lista sale vacía) y las rutas que consumen los spiders
de supermercados (ver [Ingesta de datos](#ingesta-de-datos-scraping)).

### 4. Levantar el backend

```bash
uv run uvicorn sina.main:app --reload --port 8000
```

- API en `http://localhost:8000/api/v1/...`
- Dashboards legacy (Jinja) en `http://localhost:8000/sina/gasolina`, `/sina/gas-lp`.

### 5. Levantar la SPA (React)

**Opción A — desarrollo con recarga en caliente (recomendada mientras editas UI):**

```bash
cd frontend
npm install
npm run dev                 # Vite en http://localhost:5173 (proxya /api al backend :8000)
```

Abre **http://localhost:5173**. Necesitas el backend del paso 4 corriendo en paralelo.

**Opción B — un solo origen (como en producción):**

```bash
cd frontend
npm install
npm run build               # genera frontend/dist
```

FastAPI sirve la SPA compilada directamente en **http://localhost:8000** (mismo origen que la
API, sin CORS). Útil para probar el comportamiento real de despliegue.

### 6. (Opcional) Datos de Supermercados y búsqueda semántica

- Corre los scrapers de supermercados (Soriana / Del Sol / Benavides / Farmacias Guadalajara)
  para poblar la tabla `supermercados` — ver [Ingesta de datos](#ingesta-de-datos-scraping).
- Para **embeddings + búsqueda vectorial**, pon `ENABLE_EMBEDDINGS=1` en el `.env` **antes** de
  scrapear. El modelo por defecto (`Qwen/Qwen3-Embedding-8B`) es pesado; en una PC sin GPU usa uno
  ligero, p. ej. `EMBEDDING_MODEL=intfloat/multilingual-e5-small`. Sin embeddings, la búsqueda cae
  a texto (ILIKE) y funciona igual.

> Nota: `DB_URL` se resuelve **al importar** y las tablas se crean solas en ese momento. Define el
> `.env` antes de arrancar o sembrar.

### 7. (Opcional) Chat / asistente (Fase 3)

El asistente usa **Ollama** (local) detrás de una clase abstracta `LLMProvider` (para cambiar a un
modelo patrocinado sin tocar el resto). Para habilitarlo:

```bash
ollama pull qwen2.5:7b        # un modelo que soporte tool-calling
# en .env:
#   ENABLE_CHAT=1
#   OLLAMA_MODEL=qwen2.5:7b
```

Luego abre `/chat` en la SPA. Funciona **sin login** (sin guardar historial) o **con login**
(guarda hasta `CHAT_MAX_CONVERSACIONES` conversaciones en MongoDB, paginadas por punteros). La
respuesta llega en **streaming** con botón de **pausa** (al pausar no se guarda ese intercambio).
Para "gasolina cerca de mí", el chat usa la ubicación que compartas con el botón "usar mi
ubicación" (se cachea y se comparte con el mapa de Gasolina). Si Ollama o Mongo no están, el chat
degrada con un aviso claro en vez de romper.

---

## Ingesta de datos (scraping)

SINA se alimenta de tres tipos de fuente, cada una con su propio ritmo:

| Fuente               | Cómo entra                            | Frecuencia sugerida        |
| -------------------- | ------------------------------------- | -------------------------- |
| Gasolina (CRE)       | API de gobierno, caché **on-demand**  | al consultar (refresco 24h) |
| Gas LP (CNE)         | API de gobierno, caché **on-demand**  | al consultar (refresco semanal) |
| Supermercados        | **web scraping** por catálogo de rutas | semanal (job pesado)       |

Gasolina y Gas LP se refrescan solos: la primera consulta a un municipio/localidad llama a la API
de gobierno y guarda; después se sirve de la base hasta que la caché vence. El
[scheduler](src/sina/scheduler.py) además re-scrapea en segundo plano lo que ya se consultó
(gasolina diario 06:00, gas LP sábado 08:00, hora MX).

**Los supermercados sí se scrapean explícitamente.** El flujo tiene dos etapas:

### 1. Catálogo de rutas (una vez, o cuando cambie el árbol de la tienda)

Cada tienda tiene un archivo de configuración en `src/sina/config/` con su árbol
departamento → categoría → `url_path`:

- `soriana_config.json`, `delsol_config.json`, `benavides_config.json`, `guadalajara_config.json`.

> **Farmacias Guadalajara** solo incluye las pestañas **Super**, **Farmacia** y **Dermo**.
> Se excluye **Ofertas** a propósito: es una vista promocional que re-lista los mismos
> productos (mismos `pid`) de las otras pestañas — el descuento igual se captura porque el
> spider lee el precio vigente de cada categoría.

El **seeder** (`python -m sina.db.seeder`) lee esos archivos y puebla la tabla `catalogos_config`
(una fila por ruta activa). Es idempotente: re-ejecutarlo no duplica.

Para **regenerar** un catálogo (p. ej. si la tienda reorganizó su menú), corre el explorador de
árbol correspondiente en `notebooks/` y vuelve a sembrar:

```bash
# Benavides (Magento): reconstruye benavides_config.json desde el menú del sitio
uv run python notebooks/benavides_01.py
# Farmacias Guadalajara (SFCC): reconstruye guadalajara_config.json (Super/Farmacia/Dermo)
uv run python notebooks/guadalajara_01.py
# Del Sol (VTEX): reconstruye delsol_config.json
uv run python notebooks/woolworth_01.py
uv run python -m sina.db.seeder            # re-siembra las rutas nuevas
```

### 2. Extracción de productos (periódica)

Con las rutas sembradas y **PostgreSQL arriba**, cada spider recorre las rutas activas de su
tienda, extrae productos y hace `upsert` en la tabla `supermercados`:

```bash
uv run python -m sina.scraping.supermercados.soriana_spider       # Playwright (navegador)
uv run python -m sina.scraping.supermercados.delsol_spider        # Playwright (navegador)
uv run python -m sina.scraping.supermercados.benavides_spider     # curl_cffi (sin navegador)
uv run python -m sina.scraping.supermercados.guadalajara_spider   # curl_cffi (sin navegador)
```

Notas de implementación:

- La **URL base** de cada tienda vive en el `.env` (`SORIANA_BASE_URL`, `DELSOL_BASE_URL`,
  `BENAVIDES_BASE_URL`, `GUADALAJARA_BASE_URL`); los `*_config.json` solo guardan el `url_path`.
  El spider arma la URL final = base + path. Así, si una tienda cambia de dominio, se ajusta el
  `.env` sin tocar código.
- **Soriana** y **Del Sol** usan navegador headless (Playwright + stealth); **Benavides**
  (Magento) y **Farmacias Guadalajara** (Salesforce Commerce Cloud) se renderizan en el servidor,
  así que usan `curl_cffi` — más ligeros y rápidos.
- Con `ENABLE_EMBEDDINGS=1` (solo PostgreSQL), el `upsert` genera además el embedding de cada
  producto para la búsqueda semántica.

### Automatización (crones)

Hoy la programación vive en [`scheduler.py`](src/sina/scheduler.py) (APScheduler en proceso). El
job de supermercados está **desactivado por defecto** porque es pesado (abre navegadores); se
activa con `ENABLE_SUPERMERCADOS_SCRAPING=1` y corre los domingos 04:00 (hora MX). Actívalo solo en
un **worker dedicado**, nunca en el proceso web con varias instancias (se duplicaría el trabajo).

A futuro, en GCP, estos crones se moverán a **Cloud Scheduler + Cloud Run Jobs** (contenedor con
navegador), apagando el scheduler en proceso (`ENABLE_SCHEDULER=0`) para que una sola tarea
programada sea la fuente de verdad.

---

## Pasar a un servidor patrocinado (solo cambia el `.env`)

Cuando haya un servidor (VPS, o GCP con Cloud SQL), **no se cambia código**: se ajusta el `.env`.

```dotenv
# Apuntar a la base remota (los datos NO se migran solos: hay que sembrar/scrapear allá)
DB_HOST=tu-host-postgres
DB_PORT=5432
DB_NAME=sina_db
DB_USER=usuario
DB_PASSWORD=contraseña-fuerte

# Endurecer para producción
SINA_ENV=prod                     # activa cookies Secure + HSTS
SECRET_KEY=<48+ chars aleatorios> # firma de sesión; genera con:
                                  # python -c "import secrets; print(secrets.token_urlsafe(48))"
GOOGLE_OAUTH_CLIENT_ID=<client-id-oauth-web>   # habilita el login con Google
CORS_ORIGINS=https://tu-dominio   # solo si la SPA se sirve en otro origen
ADMIN_API_KEY=<clave-admin>       # protege los endpoints de scraping/actualización
```

En un servidor dedicado, sirve el backend con varios workers:

```bash
gunicorn sina.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

Meta a mediano plazo (pendiente, Fase 5): `Containerfile` con Podman, y GCP (Cloud Run + Cloud SQL
+ Cloud Scheduler + Secret Manager). El scheduler en proceso (`ENABLE_SCHEDULER`) debe apagarse en
entornos con múltiples instancias y moverse a Cloud Scheduler.

---

## Variables de entorno

Todas se documentan en [.env.example](.env.example). Resumen:

| Variable                                                                | Para qué                                                        | Local                      |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------------- |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Conexión a PostgreSQL. Si falta alguna → SQLite.               | valores de`compose.yaml` |
| `SINA_ENV`                                                            | `dev` \| `prod` (cookies Secure + HSTS en prod).             | `dev`                    |
| `GOOGLE_OAUTH_CLIENT_ID`                                              | Client ID público de Google OAuth. Vacío = login oculto.       | opcional                   |
| `SECRET_KEY`                                                          | Firma de la sesión. Obligatoria en prod.                        | opcional en dev (efímera) |
| `SESSION_TTL`                                                         | Vida de la sesión (segundos).                                   | 14 días                   |
| `CORS_ORIGINS`                                                        | Orígenes permitidos (solo si la SPA va en otro host).           | vacío                     |
| `ADMIN_API_KEY`                                                       | Protege los`POST` de scraping/actualización.                  | vacío = cerrados          |
| `ENABLE_SCHEDULER`                                                    | Actualizaciones automáticas (gasolina diario, gas LP sábados). | `1`                      |
| `ENABLE_SUPERMERCADOS_SCRAPING`                                       | Job semanal de scraping de supermercados (pesado, opt-in).       | `0`                      |
| `*_BASE_URL` (Soriana/Del Sol/Benavides/Guadalajara)                | Dominio base de cada tienda (el `url_path` vive en su config).   | dominios oficiales         |
| `ENABLE_EMBEDDINGS`                                                   | Genera embeddings al scrapear productos (solo PostgreSQL).       | `0`                      |
| `ENABLE_CHAT`                                                        | Habilita el asistente en`POST /api/v1/chat`.                    | `0`                      |
| `LLM_PROVIDER` / `OLLAMA_HOST` / `OLLAMA_MODEL`                    | Proveedor LLM y Ollama (modelo con tool-calling).                | ollama / :11434 / qwen2.5:7b |
| `MONGO_URI` / `MONGO_DB`                                            | Historial de chat (local; cambia la URI al patrocinar).          | localhost:27017 / sina     |
| `CHAT_MAX_CONVERSACIONES` / `CHAT_CHUNK_SIZE`                      | Conversaciones por usuario y mensajes por bucket.                | 5 / 15                     |
| `EMBEDDING_MODEL`                                                     | Modelo de embeddings (intercambiable).                           | Qwen (pesado)              |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW`                                  | Tamaño del pool de conexiones.                                  | 5 / 5                      |
| `GOOGLE_API_KEY`                                                      | Clave de Gemini para OCR de volantes (no es OAuth).              | opcional                   |

---

## API (endpoints activos)

Base: `/api/v1`.

| Método     | Ruta                                                     | Descripción                                                                    |
| ----------- | -------------------------------------------------------- | ------------------------------------------------------------------------------- |
| GET         | `/health`                                              | Última actualización + vigencia por categoría.                               |
| GET         | `/config`                                              | Config pública del cliente (client ID de Google).                              |
| GET         | `/catalogo`                                            | Catálogo`{ estado: [municipios] }` para los selectores.                      |
| GET         | `/gasolina?estado&municipio`                           | Precios de gasolina (caché 24h on-demand).                                     |
| GET         | `/gas-lp?estado&municipio&localidad`                   | Precios de Gas LP (caché semanal).                                             |
| GET         | `/gas-lp/localidades?estado&municipio`                 | Localidades disponibles.                                                        |
| GET         | `/gas-lp/by-ids?entidad_id&municipio_id&localidad_id`  | Precios por IDs (preferido para UI).                                            |
| GET         | `/supermercados?q&tienda&departamento&categoria&limit` | Búsqueda de productos (semántica o texto).                                    |
| POST        | `/auth/google`                                         | Verifica el ID token de Google y abre sesión.                                  |
| POST        | `/auth/logout`                                         | Cierra sesión.                                                                 |
| GET / PATCH | `/me`                                                  | Perfil del usuario / fijar`username`.                                         |
| POST        | `/chat`                                                | Asistente en **streaming SSE** (anónimo o con sesión). Con login persiste en Mongo. |
| GET/POST/DELETE | `/chat/conversaciones[...]`                        | Conversaciones (máx 5) + carga de mensajes por puntero. Requiere sesión.        |
| POST        | `/update/gasolina`, `/update/ubicacion/gasolineras`  | Actualización manual (requiere`ADMIN_API_KEY`).                              |
| POST/GET    | `/annotator/*`                                         | Herramientas de anotación de volantes (mutaciones requieren`ADMIN_API_KEY`). |

La SPA se sirve en `/` (y sus rutas de cliente `/gasolina`, `/gas-lp`, `/supermercados`, `/chat`)
cuando existe `frontend/dist`.

---

## Estructura del proyecto

```
sina/
├── compose.yaml               # Podman Compose: PostgreSQL 16 + pgvector
├── pyproject.toml             # dependencias (uv)
├── .env.example               # plantilla de variables
├── SPEC.md · CLAUDE.md        # visión / guía de desarrollo
├── src/sina/
│   ├── main.py                # FastAPI: endpoints + montaje de la SPA
│   ├── scheduler.py           # APScheduler (gasolina diario, gas LP sábados, supermercados opt-in)
│   ├── agent/                 # Chat (Fase 3): llm/ (LLMProvider+Ollama), tools/, graph.py, agent.py, geo.py
│   ├── api/                   # auth.py, users.py, chat.py, deps.py, session.py, security.py, ratelimit.py
│   ├── config/                # credentials.py, app_settings.py, paths.py, timezone.py, logging_config.py
│   ├── db/                    # models.py, repository.py, seeder.py, mongo.py, chat_store.py
│   ├── scraping/
│   │   ├── gobierno/          # cre_gasolina.py, cne_gas_lp.py (APIs de gobierno)
│   │   └── supermercados/     # soriana_spider.py, delsol_spider.py, benavides_spider.py, guadalajara_spider.py, casaley_spider.py
│   ├── embedder/              # base.py (ABC) + qwen_embedder.py + embeddings.py
│   ├── annotator/             # image_segmentation.py, records.py
│   └── ollama/                # extract_flyer_text.py (OCR/LLM)
├── frontend/                  # SPA React (Vite + React 19 + Tailwind v4)
│   └── src/{pages,features,components,hooks,lib}
├── templates/ · static/       # dashboards Jinja legacy (en migración)
└── datos/                     # artefactos scrapeados + SQLite de dev
```

---

## Comandos útiles

```bash
# Podman / PostgreSQL
podman-compose up -d                 # levantar la base
podman-compose logs -f               # ver logs
podman-compose down                  # detener
podman-compose down -v               # detener y borrar el volumen (datos)
podman exec -it sina_db psql -U sina_admin -d sina_db   # consola SQL
podman exec -it sina_mongo mongosh sina                 # consola de MongoDB (historial de chat)

# Backend
uv run uvicorn sina.main:app --reload --port 8000
uv run python -m sina.db.seeder      # sembrar catálogos (municipios + rutas de scraping)

# Ingesta de supermercados (requiere PostgreSQL + catálogos sembrados)
uv run python -m sina.scraping.supermercados.soriana_spider
uv run python -m sina.scraping.supermercados.delsol_spider
uv run python -m sina.scraping.supermercados.benavides_spider
uv run python -m sina.scraping.supermercados.guadalajara_spider

# Frontend
cd frontend && npm run dev           # desarrollo (:5173)
cd frontend && npm run build         # compilar (lo sirve FastAPI en :8000)
```

---

## Roadmap (resumen de [SPEC.md](SPEC.md))

| Fase | Objetivo                                                       | Estado                                                             |
| ---- | -------------------------------------------------------------- | ------------------------------------------------------------------ |
| 1    | Estabilizar backend (PostgreSQL + pgvector, scheduler, health) | Hecho                                                              |
| 2    | Pipeline de supermercados + embeddings (core)                  | Hecho (base)                                                       |
| 3    | Capa de agente / chat con tools internas                       | Hecho (base): Ollama + tools + grafo, `/chat` SSE, historial Mongo |
| 4    | SPA React + Google OAuth                                       | En curso (landing, auth y dashboards hechos; chat "próximamente") |
| 5    | Calidad y despliegue (tests, CI/CD, Containerfile, GCP)        | Pendiente                                                          |
| 6    | ML de volantes (detección de zonas)                           | Largo plazo                                                        |

---

## Licencia

MIT — ver [LICENSE](LICENSE).

<div align="center">
© 2026 SINA — Sistema de Información Nacional de Ahorro
</div>
