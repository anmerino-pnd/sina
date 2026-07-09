# SINA — Sistema de Información Nacional de Ahorro

<div align="center">

---

## Qué es

SINA centraliza precios de primera necesidad y los sirve en dashboards + una API REST:

- **Gasolina** — API de la CRE (Magna, Premium, Diésel por estación, con mapa).
- **Gas LP** — API de la CNE (precio por kilo por permisionario y localidad).
- **Supermercados** — scraping directo (Soriana, Del Sol; volantes de Casa Ley como track
  secundario) con búsqueda por texto y **semántica (pgvector)**.

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
| Chat / asistente conversacional                                     | **Pendiente** (UI muestra "próximamente") |
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
- **Podman** + **podman-compose** (para PostgreSQL local). En Windows, con WSL2.

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

### 2. Levantar PostgreSQL + pgvector con Podman

```bash
podman-compose up -d        # arranca el contenedor sina_db (pgvector/pgvector:pg16)
```

### 3. Sembrar catálogos

```bash
uv run python -m sina.db.seeder
```

Esto carga entidades/municipios/**localidades** y el catálogo de Soriana. Es lo que habilita las
localidades del dashboard de **Gas LP** (sin seeder, esa lista sale vacía).

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

- Corre los scrapers de supermercados (Soriana / Del Sol) para poblar la tabla `supermercados`.
- Para **embeddings + búsqueda vectorial**, pon `ENABLE_EMBEDDINGS=1` en el `.env` **antes** de
  scrapear. El modelo por defecto (`Qwen/Qwen3-Embedding-8B`) es pesado; en una PC sin GPU usa uno
  ligero, p. ej. `EMBEDDING_MODEL=intfloat/multilingual-e5-small`. Sin embeddings, la búsqueda cae
  a texto (ILIKE) y funciona igual.

> Nota: `DB_URL` se resuelve **al importar** y las tablas se crean solas en ese momento. Define el
> `.env` antes de arrancar o sembrar.

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
| `ENABLE_EMBEDDINGS`                                                   | Genera embeddings al scrapear productos (solo PostgreSQL).       | `0`                      |
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
│   ├── scheduler.py           # APScheduler (gasolina diario, gas LP sábados)
│   ├── api/                   # auth.py, users.py, deps.py, session.py, security.py, ratelimit.py
│   ├── config/                # credentials.py, app_settings.py, paths.py, timezone.py, logging_config.py
│   ├── db/                    # models.py, repository.py, seeder.py
│   ├── scraping/
│   │   ├── gobierno/          # cre_gasolina.py, cne_gas_lp.py (APIs de gobierno)
│   │   └── supermercados/     # soriana_spider.py, delsol_spider.py, casaley_spider.py
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

# Backend
uv run uvicorn sina.main:app --reload --port 8000
uv run python -m sina.db.seeder      # sembrar catálogos

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
| 3    | Capa de agente / chat con tools internas                       | Pendiente                                                          |
| 4    | SPA React + Google OAuth                                       | En curso (landing, auth y dashboards hechos; chat "próximamente") |
| 5    | Calidad y despliegue (tests, CI/CD, Containerfile, GCP)        | Pendiente                                                          |
| 6    | ML de volantes (detección de zonas)                           | Largo plazo                                                        |

---

## Licencia

MIT — ver [LICENSE](LICENSE).

<div align="center">
© 2026 SINA — Sistema de Información Nacional de Ahorro
</div>
