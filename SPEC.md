# SPEC.md — Proyecto SINA

## Sistema de Información Nacional de Ahorro

---

## 1. Visión y Propósito

SINA es una plataforma pública que ayuda a las familias mexicanas a cuidar su economía:
les muestra dónde encontrar más barato lo que necesitan (combustibles y despensa) y les
permite tomar decisiones de compra informadas.

**Misión:** Empoderar a la familia mexicana con información clara y accesible de precios de
primera necesidad, para que gaste menos o le afecte lo menos posible.

**Público objetivo:**
- Familias y ciudadanos en general (amas de casa, trabajadores, estudiantes).
- Personas con baja alfabetización digital (de ahí el chat conversacional).
- Municipios / gobierno local (para patrocinio y presentación).

**Alcance geográfico (por fases):**
1. Hermosillo, Sonora (MVP)
2. Estado de Sonora completo
3. Zona Norte de México
4. Centro y Sur de México

**Modelo de acceso:**
- Dashboards (Gasolina, Gas LP, Supermercados): 100% público, sin login.
- Chat: funcional sin login (el historial se pierde al recargar).
- Chat con historial persistente: requiere Google OAuth 2.0.
- Nunca se almacenan contraseñas.

---

## 2. Arquitectura del Sistema

### 2.1 Stack Tecnológico

| Capa          | Actual                          | Producción (meta)                          |
| ------------- | ------------------------------- | ------------------------------------------ |
| Backend       | FastAPI (Python 3.12+)          | FastAPI + jobs de scraping programados     |
| Frontend      | HTML/CSS/JS + Jinja2 (por vista)| React SPA (Vite + Tailwind, "Liquid Glass")|
| Base de Datos | PostgreSQL 16 + pgvector        | PostgreSQL 16 + pgvector (Cloud SQL en GCP)|
| ORM           | SQLAlchemy + Repository Pattern | igual                                      |
| Embeddings    | `EmbeddingProvider` abstracto: open-source local (Qwen / sentence-transformers) | + proveedor privado intercambiable (si hay patrocinio) |
| LLM           | `LLMProvider` abstracto: open-source local (Ollama / llama.cpp) | + `GeminiProvider` en GCP |
| Mapas         | Leaflet.js                      | Leaflet.js                                 |
| Scheduling    | APScheduler en lifespan (+ endpoints POST manuales) | APScheduler / Cloud Scheduler |
| Empaquetado   | uv (deps) + Podman (compose DB) | Podman / Containerfile (no Docker)         |
| Deploy        | Local                           | PC / servidor dedicado / GCP (Cloud Run)   |

> **Nota — SQLite quedó descartado.** Al ejecutar los scrapers de ubicaciones de gasolineras
> y de localidades por municipio, el volumen de datos hizo inviable SQLite. Se adoptó
> **PostgreSQL + pgvector**: PostgreSQL aguanta el volumen y pgvector permite guardar
> embeddings de productos para búsqueda semántica. SQLite queda solo como *fallback* de
> desarrollo (ver `get_db_url()` en `config/credentials.py`).

### 2.2 Patrón Arquitectónico (meta)

```
┌─────────────────────────────────────────────────────────┐
│ USUARIO (navegador)                                       │
│   React SPA: / · /gasolina · /gas-lp · /supermercados · /chat │
└───────────────┬───────────────────────────┬──────────────┘
        Dashboards                         Chat
                │                            │
                ▼                            ▼
┌─────────────────────────────────────────────────────────┐
│ FastAPI Backend                                           │
│  /api/v1/gasolina   /api/v1/gas-lp   /api/v1/supermercados│
│  /api/v1/chat  ──► Capa de Agente (tools internas)        │
└───────────────┬─────────────────────────┬────────────────┘
                │                          │
                ▼                          ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│ Repository Pattern + Cache│   │ LLMProvider (abstracto)   │
│ (SQLAlchemy)              │   │  · OpenSource (Ollama/    │
└────────────┬─────────────┘   │    llama.cpp) — local     │
             │                 │  · Gemini — GCP           │
             ▼                 └──────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ PostgreSQL 16 + pgvector                                  │
│  precios (gasolina, gas LP) · productos + embeddings ·    │
│  catálogos CNE · config de scraping · usuarios / chat     │
└─────────────────────────────────────────────────────────┘
        ▲
        │ scrapers (gobierno: requests · supermercados: Playwright/Selenium)
```

### 2.3 Estrategia de Datos (Caching Inteligente)

| Categoría     | Frecuencia        | Trigger                                  |
| ------------- | ----------------- | ---------------------------------------- |
| Gasolina      | Diaria (AM)       | Usuario busca + datos > 24h              |
| Gas LP        | Semanal (sábado)  | Usuario busca + datos > último sábado    |
| Supermercados | Programada        | Scraping directo (Soriana, Del Sol, Benavides, Guadalajara) |
| Ubicaciones   | Una vez + updates | Scraping inicial, luego solo cambios     |

**Regla general:** si el usuario busca un lugar y los datos están vigentes → se sirve de
caché; si vencieron → se llama a la API de gobierno / se re-scrapea → se guarda en DB →
se responde.

**Datos inexistentes:** si un municipio no tiene datos de una categoría, mostrar aviso
("De momento no tenemos datos de [categoría] para [municipio]…") y filtrar dinámicamente
los selectores Estado/Municipio según la categoría.

---

## 3. Estado Actual del Proyecto

### 3.1 Módulos

| Módulo                          | Estado | Notas                                                      |
| ------------------------------- | ------ | ---------------------------------------------------------- |
| Pipeline + API Gasolina         | ✅     | API CRE + caché 24h on-demand. Falta scheduler automático. |
| UI Gasolina (Jinja2)            | ✅     | Mapa + ranking. Migra a SPA preservando funciones.         |
| Scraper ubicaciones gasolineras | ✅     | Código listo; se corre puntualmente.                       |
| Pipeline + API Gas LP           | ✅     | API CNE + caché semanal. Falta scheduler automático.       |
| UI Gas LP (Jinja2)              | ✅     | Cascada estado→municipio→localidad. Migra a SPA.           |
| Scraping Soriana                | ✅     | SFCC; Playwright; `upsert` a tabla `supermercados` (mapeo `pid_origen`→`pid`). |
| Scraping Del Sol                | ✅     | VTEX; Playwright async; `upsert` a `supermercados`.        |
| Scraping Benavides              | ✅     | Magento; `curl_cffi` (server-side, sin navegador); paginación `?p=N`. |
| Scraping Farmacias Guadalajara  | ✅     | SFCC; `curl_cffi`; paginación "Show More" SFCC; pestañas Super/Farmacia/Dermo (Ofertas excluida por solaparse). |
| Embeddings de productos         | ✅*    | Conectados en `upsert_productos` (opt-in `ENABLE_EMBEDDINGS`, requiere pgvector). |
| Búsqueda / API Supermercados    | ✅     | `GET /api/v1/supermercados` (vectorial con fallback de texto). Falta UI. |
| Agente / Chat (tools internas)  | ✅     | `sina/agent/` (LLM Ollama + tools + grafo); `POST /api/v1/chat` en streaming SSE; historial en MongoDB. |
| Pipeline volantes (Casa Ley)    | ✅*    | Descarga flyer + anotación manual + OCR LLM. Track secundario. |
| QQP / PROFECO                   | 🗑️     | **Deprecado** (modelo/repo conservados con aviso; endpoints removidos). |
| Scheduling automático           | ✅     | APScheduler en lifespan (`scheduler.py`); gasolina 06:00, gas LP sáb 08:00. |
| Logging + health check          | ✅     | Logging unificado (`logging_config.py`); `GET /api/v1/health`. |
| React SPA                       | ✅     | Vite + React + Tailwind. Landing, Gasolina, Gas LP y Supermercados + modo oscuro. Chat en "próximamente". |
| Google OAuth                    | ✅     | Login con Google (sesión en cookie httpOnly + CSRF); tablas `usuarios`/`chat_historial`. Requiere configurar `GOOGLE_OAUTH_CLIENT_ID`. |
| Tests / CI-CD / Containerfile   | ❌     | No existen (Fase 5).                                       |

### 3.2 Pendientes críticos inmediatos

- [x] Fijar PostgreSQL + pgvector como base por defecto (extensión `vector` auto-creada en
      `repository.py`; `.env.example` alineado con `compose.yaml`).
- [x] Deprecar QQP/PROFECO sin borrarlo (modelo `PrecioQQP` y `QQPRepository` conservados con
      aviso `DeprecationWarning`, por si se reactiva).
- [x] Scheduler automático (gasolina diario 06:00, gas LP sábados 08:00; hora MX).
- [ ] Conectar embeddings al `upsert_productos()` y añadir búsqueda vectorial. *(Fase 2)*
- [ ] Endpoint + consulta de supermercados. *(Fase 2)*

---

## 4. Fases de Desarrollo

### FASE 1 — Estabilización del Backend ✅
**Meta:** que gasolina y gas LP corran solos y la base sea PostgreSQL.
- [x] PostgreSQL + pgvector como default; SQLite solo fallback dev. La extensión `vector` se
      crea automáticamente al arrancar (`repository.py`) y `.env.example` coincide con `compose.yaml`.
- [x] Deprecar QQP/PROFECO **sin borrar** (modelo `PrecioQQP` + `QQPRepository` con
      `DeprecationWarning`; la tabla se sigue creando por si se reactiva).
- [x] APScheduler en el `lifespan` de FastAPI (`sina/scheduler.py`), controlado por
      `ENABLE_SCHEDULER`:
  - Gasolina: diario 6:00 AM (hora centro MX)
  - Gas LP: sábados 8:00 AM
  - Refresca solo ubicaciones/localidades ya presentes en la DB, reutilizando la caché on-demand.
- [x] Logging unificado consola + archivo rotativo (`sina/config/logging_config.py`,
      `logs/sina.log`). El fallback "servir datos vencidos con aviso" ya existe en
      `get_precios_gasolina()` / `get_precios_gas_lp()` (fuente `cache_vencido`).
- [x] Health check `GET /api/v1/health` con última actualización + vigencia por categoría.

### FASE 2 — Pipeline de Supermercados + Embeddings (CORE) ✅ (base)
**Meta:** convertir el scraping directo en una base de productos consultable y vectorizada.
- [x] Scraping directo como fuente primaria (Soriana, Del Sol, **Benavides**, **Farmacias
      Guadalajara**). Se corrigió el bug latente: `upsert_productos` mapea `pid_origen`→`pid` y
      normaliza al esquema del modelo. El seeder es genérico (`seed_catalogo_tienda` +
      `TIENDAS_CATALOGO`), la URL base de cada tienda vive en `.env`, y hay job semanal opt-in de
      scraping en `scheduler.py` (`ENABLE_SUPERMERCADOS_SCRAPING`). *(Ampliar a más tiendas: seguir sumando.)*
- [x] Normalización básica de nombres (espacios) y **dedup por `pid`** dentro del lote (evita
      el choque en `ON CONFLICT`). *(Dedup semántico cross-tienda: futuro.)*
- [x] **Embeddings conectados**: `upsert_productos` invoca `EmbeddingService.vectorizar_productos()`
      (batch) y puebla `Supermercado.embedding` cuando `ENABLE_EMBEDDINGS=1` (solo PostgreSQL).
      Provider perezoso vía `EmbeddingProvider` abstracto (open-source ↔ privado), modelo
      configurable con `EMBEDDING_MODEL`.
- [x] Búsqueda vectorial sobre pgvector (coseno, `cosine_distance`) + filtros duros
      (tienda/departamento/categoría), con **fallback de texto** (ILIKE) si no hay embeddings.
      *(Nota: el modelo `supermercados` aún no tiene ubicación; filtro por municipio = futuro.)*
- [x] Endpoint `GET /api/v1/supermercados` (filtros + búsqueda) para SPA y agente.
- Volantes (Casa Ley → annotator → OCR LLM) se mantienen como **track secundario** para
  tiendas sin sitio scrapeable.

### FASE 3 — Capa de Agente (tools internas) ✅ (base; falta Gemini y streaming SSE avanzado)
**Meta:** un asistente conectado a la DB que resuelve consultas de ahorro.
- [x] `LLMProvider` (ABC) en `sina/agent/llm/base.py` con `chat_stream` (+ `chat`) y telemetría
      `LLMUso`. `OllamaProvider` (open-source local) implementado; fábrica perezosa gated por
      `ENABLE_CHAT` y elegida por `LLM_PROVIDER` (`GeminiProvider` = hueco listo para el patrocinador,
      hereda de la ABC y recibe las MISMAS tools).
- [x] Tools internas (Python) sobre los repositorios (`sina/agent/tools/`): `buscar_gasolina`
      (precio o cercanía por haversine), `buscar_gas_lp`, `listar_localidades_gas_lp`,
      `buscar_producto` (vectorial + filtro), `comparar_lista`, `armar_canasta`, `datos_disponibles`.
      Cada tool cierra sobre un `ContextoConsulta` (el `lat/lng` se INYECTA, el LLM no lo alucina).
- [x] **Motor de grafo propio** (`sina/agent/graph.py`, estilo LangGraph **sin** LangChain/LangGraph):
      nodos `agente ↔ tools` con router condicional e iteraciones acotadas (`LLM_MAX_ITERS`).
- [x] Manejo de ubicación: se pasa por request (nunca se persiste en servidor); el frontend la
      captura de forma no intrusiva (botón) y la cachea compartida con Gasolina.
- [x] `POST /api/v1/chat` en **streaming SSE** con **pausa** (abortar = no se persiste); funciona sin
      login (sin persistencia) y con login (guarda en Mongo). CSRF condicional + rate limit.
- [x] **Telemetría por mensaje** (para optimizar): modelo, input/output/cached tokens, tokens/seg,
      duración, `tool_timings` y `phase_timings`.
- **Sin servidor MCP por ahora**; las tools viven dentro del backend. Empaquetarlas como
  servidor MCP estándar queda como posible evolución futura.
- [ ] Pendiente: `GeminiProvider` real (con `cached_tokens`), y streaming SSE "premium" (reintentos).

### FASE 4 — SPA React + OAuth ✅ (base; falta solo el chat, que depende de Fase 3)
**Meta:** unificar todo en una sola app moderna.
- [x] Setup: Vite + React 19 + React Router + Tailwind v4, mobile-first. En lugar del
      glassmorphism completo se optó por un estilo **editorial sobrio** (paleta del colibrí de
      Costa) + **modo oscuro**, con vidrio esmerilado solo en navbar y controles del mapa
      (mejor contraste/accesibilidad; se aleja del look "IA").
- [x] Rutas: `/` (landing), `/gasolina`, `/gas-lp`, `/supermercados`, `/chat`.
- [x] **Gasolina — REFACTOR:** migrado a React conservando todas las funciones (mapa Leaflet,
      autocomplete/cascada, ranking, filtro por categoría en el mapa, calculadora con
      comparación base/seleccionada, "cerca de ti", geolocalización, vigencia). Layout de 3
      paneles responsivo.
- [x] **Gas LP — REFACTOR:** cascada estado→municipio→localidad, pills de tipo/capacidad,
      ranking y detalle de proveedor con vigencia.
- [x] **Supermercados — NUEVA:** búsqueda (con debounce) + filtro por tienda + tabla de precios.
- [x] **Chat — NUEVA:** `ChatPage` conversacional contra `/api/v1/chat` (streaming SSE + botón de
      pausa). Con login: panel de conversaciones (máx 5) y "cargar mensajes anteriores" (paginación
      por puntero). Chip de ubicación no intrusivo compartido con Gasolina. Sustituyó a
      `ChatUnavailable` sin cambiar la ruta.
- [x] Google OAuth 2.0: botón en navbar; sin login todo funciona sin persistencia. Sesión propia
      en **cookie httpOnly + Secure + SameSite firmada** con **CSRF double-submit** (nunca se
      guardan contraseñas ni el token de Google; el `user_id` es el `sub` de Google, con
      `username` opcional). Tablas `usuarios` y `chat_historial` creadas.
- [x] **Extra entregado (adelanto de Fase 5):** la SPA se sirve desde FastAPI en el mismo origen
      (mount `/assets` + catch-all), `GET /api/v1/catalogo` para los selectores, endurecimiento
      (cabeceras CSP/HSTS, CORS por allowlist, rate limiting con slowapi, cierre de los `POST`
      de scraping tras `ADMIN_API_KEY`) y tuning del pool de conexiones.
- [ ] **Pendiente menor:** `favoritos` y `alertas` (Fase 4+); persistencia del historial de chat
      (ligada a Fase 3).

### FASE 5 — Calidad y Despliegue (Producción)
**Meta:** que sea desplegable y mantenible siguiendo buenas prácticas.
- [ ] Tests con pytest (unit de repositorios/tools; integración de endpoints; mocks de
      scrapers y de gobierno).
- [ ] CI/CD con GitHub Actions: lint + tests en PR; build de imagen al hacer merge.
- [ ] Empaquetado con **Podman** (`Containerfile`, no Docker); `compose` para app + Postgres.
- [ ] Deploy multi-destino:
  - Local / PC (Podman compose)
  - Servidor dedicado (mismo contenedor)
  - **GCP (meta):** Cloud Run para el backend + Cloud SQL (PostgreSQL + pgvector); jobs de
    scraping vía Cloud Scheduler / Cloud Run Jobs; secretos en Secret Manager.
- [ ] Buscar patrocinador para el servidor / dominio (p. ej. `sina.mx`).

### FASE 6 — Automatización ML de Volantes (Largo Plazo)
**Meta:** reducir la anotación manual de volantes.
- Acumular dataset del annotator (~500+ imágenes anotadas).
- Entrenar detección de zonas (p. ej. Roboflow) e integrarla al pipeline OCR existente.
- Expansión geográfica de volantes (Hermosillo → Sonora → Norte → Centro/Sur).

---

## 5. Esquema de Base de Datos

### Tablas actuales

| Tabla            | Propósito                                              |
| ---------------- | ------------------------------------------------------ |
| `gasolineras`    | Precios + ubicaciones (PK `numero`; magna/premium/diesel). |
| `gas_lp_precios` | Precios Gas LP por permisionario/localidad (desnormalizado). |
| `supermercados`  | Productos + precios + **embedding** (pgvector).        |
| `catalogos_config`| Rutas activas de scraping (Soriana, Del Sol, Benavides, Guadalajara). |
| `cne_entidades` / `cne_municipios` / `cne_localidades` | Catálogos geográficos CNE. |
| `qqp_precios`    | 🗑️ **Legacy — a eliminar** (reemplazado por `supermercados`). |

### Tablas nuevas

| Tabla            | Propósito                          | Fase |
| ---------------- | ---------------------------------- | ---- |
| `usuarios`       | Usuarios Google OAuth (sin pwd)    | 4 ✅ (creada) |
| `chat_historial` | 🗑️ **Deprecada** — el historial vive en MongoDB (ver abajo) | 4 → 3 |
| `favoritos`      | Gasolineras/productos guardados    | 4+   |
| `alertas`        | "Avísame si baja de $X" (futuro)   | 4+   |

### Historial de chat en MongoDB (Fase 3)

El chat NO usa PostgreSQL: por ser documental y con paginación por punteros, vive en **MongoDB**
(local por ahora; al patrocinar un servidor solo cambia `MONGO_URI`). Máximo `CHAT_MAX_CONVERSACIONES`
(5) conversaciones por usuario. Patrón **bucket / lista ligada** (estilo WhatsApp/Messenger):

| Colección        | Propósito                                                              |
| ---------------- | ---------------------------------------------------------------------- |
| `conversaciones` | `{google_sub, titulo, cabeza_chunk_id→chunk más reciente, num_mensajes, ultimo_preview}` |
| `chat_chunks`    | `{conversacion_id, mensajes:[…≤CHAT_CHUNK_SIZE], anterior_id→chunk más viejo, seq}` — se pagina hacia atrás siguiendo `anterior_id` |

Si Mongo no está disponible, el chat sigue funcionando **sin** persistencia (degradación elegante).

---

## 6. Capa de Agente y Tools (detalle)

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, context: dict) -> str: ...

class OpenSourceProvider(LLMProvider): ...  # Ollama / llama.cpp (local)
class GeminiProvider(LLMProvider): ...       # GCP

# Misma estrategia para embeddings (ver embedder/base.py):
class EmbeddingProvider(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]: ...

class QwenHuggingFaceProvider(EmbeddingProvider): ...  # open-source local (actual)
# + proveedor privado intercambiable si hay patrocinio, sin tocar el pipeline.
```

Consultas que el agente debe resolver (ejemplos):
- **Gasolina:** "¿Dónde está la gasolina más barata cerca de mí?", "¿Cuánto cuesta la premium en Hermosillo?"
- **Gas LP:** "¿Qué proveedor de gas es más barato en [localidad]?", "¿Cuándo se actualizan los precios?"
- **Supermercados:** "¿Dónde está más barata la leche?", "Tengo esta lista: […], ¿dónde me sale más barato?"
- **General:** "¿Cuánto me ahorro si cambio de gasolinera?", "Explícame más sencillo" (accesibilidad).

Las tools consultan los repositorios existentes (`GasolinaRepository`, `GasLPRepository`,
`SupermercadoRepository`) y, para productos, combinan **filtro duro + similitud vectorial**.

---

## 7. Estrategia de Despliegue

- **Empaquetado:** Podman (no Docker). `Containerfile` para el backend; `compose.yaml` para
  app + PostgreSQL/pgvector.
- **Destinos:** PC local · servidor dedicado · **GCP (norte)**.
- **GCP (objetivo):** Cloud Run (backend) + Cloud SQL PostgreSQL con pgvector + Cloud
  Scheduler/Jobs para el scraping + Secret Manager para credenciales. El flujo
  extraer → limpiar → guardar → servir UI encaja bien en este modelo serverless.

---

## 8. Criterios de "Listo para Producción"

Para presentar a un municipio / patrocinador:
- [x] Los 3 dashboards (Gasolina, Gas LP, Supermercados) funcionando en la SPA.
- [x] Datos actualizándose automáticamente (scheduler).
- [x] UI profesional, responsive (mobile-first) — incluye modo oscuro.
- [ ] Desplegado en servidor público con dominio propio.
- [ ] Tests + CI/CD verdes.
- [ ] Página "Acerca de" con el propósito del proyecto.
- [ ] Métricas básicas (usuarios, consultas/día).

**Nice to have:** chat funcional con datos reales y mensaje de impacto
("una familia puede ahorrar $X al mes usando SINA").
