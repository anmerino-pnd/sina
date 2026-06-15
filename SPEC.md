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
| Supermercados | Programada        | Scraping directo (Soriana, Del Sol, …)   |
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
| Scraping Soriana                | ✅     | Playwright; `upsert` a tabla `supermercados` (mapeo `pid_origen`→`pid`). |
| Scraping Del Sol                | ✅     | Playwright async; `upsert` a `supermercados`.              |
| Embeddings de productos         | ✅*    | Conectados en `upsert_productos` (opt-in `ENABLE_EMBEDDINGS`, requiere pgvector). |
| Búsqueda / API Supermercados    | ✅     | `GET /api/v1/supermercados` (vectorial con fallback de texto). Falta UI. |
| Agente / Chat (tools internas)  | ❌     | `chat.py` vacío. Por construir.                            |
| Pipeline volantes (Casa Ley)    | ✅*    | Descarga flyer + anotación manual + OCR LLM. Track secundario. |
| QQP / PROFECO                   | 🗑️     | **Deprecado** (modelo/repo conservados con aviso; endpoints removidos). |
| Scheduling automático           | ✅     | APScheduler en lifespan (`scheduler.py`); gasolina 06:00, gas LP sáb 08:00. |
| Logging + health check          | ✅     | Logging unificado (`logging_config.py`); `GET /api/v1/health`. |
| React SPA                       | ❌     | Por construir (Fase 4).                                    |
| Google OAuth                    | ❌     | Fase 4.                                                     |
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
- [x] Scraping directo como fuente primaria (Soriana, Del Sol). Se corrigió el bug latente:
      `upsert_productos` mapea `pid_origen`→`pid` y normaliza al esquema del modelo.
      *(Ampliar a más tiendas: pendiente.)*
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

### FASE 3 — Capa de Agente (tools internas)
**Meta:** un asistente conectado a la DB que resuelve consultas de ahorro.
- [ ] `LLMProvider` (ABC) con `generate(prompt, context)`:
  - `OpenSourceProvider` (Ollama / llama.cpp) — local.
  - `GeminiProvider` — para el servidor GCP.
- [ ] Tools internas (Python) sobre los repositorios, p. ej.:
  - `buscar_gasolina_barata(municipio, tipo)`
  - `buscar_gas_lp(localidad)`
  - `buscar_producto(producto, municipio)` (vectorial + filtro)
  - `comparar_lista_de_compras(items, municipio)` → dónde sale más barato
  - `armar_canasta_economica(municipio, presupuesto?)`
- [ ] Router de intención → tool → el LLM redacta la respuesta en lenguaje sencillo.
- [ ] Manejo de ubicación (geolocalización opcional; si no, preguntar municipio una vez).
- [ ] `POST /api/v1/chat` (funciona sin login; sin persistencia si no hay sesión).
- **Sin servidor MCP por ahora**; las tools viven dentro del backend. Empaquetarlas como
  servidor MCP estándar queda como posible evolución futura.

### FASE 4 — SPA React + Liquid Glass + OAuth
**Meta:** unificar todo en una sola app moderna.
- Setup: Vite + React + React Router + Tailwind. Tema light, glassmorphism, mobile-first.
- Rutas: `/` (landing), `/gasolina`, `/gas-lp`, `/supermercados`, `/chat`.
- **Gasolina y Gas LP — REFACTOR (no rehacer):** migrar a React **conservando todas las
  secciones y funciones actuales** (mapa Leaflet, autocomplete/cascada de selectores, tabla
  ranking, comparador por proveedor, indicador de vigencia). Cambia el diseño, no el alcance.
- **Supermercados — NUEVA:** tabla/comparador de productos por tienda con filtros y búsqueda.
- **Chat — NUEVA:** UI conversacional contra `/api/v1/chat`.
- Google OAuth 2.0: botón en navbar; sin login todo funciona sin persistencia; con login se
  guarda historial. Tablas `usuarios` y `chat_historial`.

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
| `catalogos_config`| Rutas activas de scraping (Soriana, etc.).            |
| `cne_entidades` / `cne_municipios` / `cne_localidades` | Catálogos geográficos CNE. |
| `qqp_precios`    | 🗑️ **Legacy — a eliminar** (reemplazado por `supermercados`). |

### Tablas nuevas

| Tabla            | Propósito                          | Fase |
| ---------------- | ---------------------------------- | ---- |
| `usuarios`       | Usuarios Google OAuth (sin pwd)    | 4    |
| `chat_historial` | Conversaciones persistidas         | 4    |
| `favoritos`      | Gasolineras/productos guardados    | 4+   |
| `alertas`        | "Avísame si baja de $X" (futuro)   | 4+   |

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
- Los 3 dashboards (Gasolina, Gas LP, Supermercados) funcionando en la SPA.
- Datos actualizándose automáticamente (scheduler).
- UI profesional, responsive (mobile-first).
- Desplegado en servidor público con dominio propio.
- Tests + CI/CD verdes.
- Página "Acerca de" con el propósito del proyecto.
- Métricas básicas (usuarios, consultas/día).

**Nice to have:** chat funcional con datos reales y mensaje de impacto
("una familia puede ahorrar $X al mes usando SINA").
