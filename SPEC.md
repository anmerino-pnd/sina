# SPEC.md — Proyecto SINA

## Sistema de Información Nacional de Ahorro

---

## 1. Visión y Propósito

SINA es una plataforma pública de consulta de precios de productos y servicios de primera necesidad en México (Gasolina, Gas LP, Supermercados).

**Misión:**

Empoderar al ciudadano mexicano con información clara y accesible para tomar mejores decisiones de compra y ahorro.

**Público objetivo:**

* Ciudadanos en general (amas de casa, trabajadores, estudiantes)
* Personas adultas con baja alfabetización digital (por eso el chatbot)
* Municipios y gobierno local (presentación para patrocinio)

**Alcance geográfico (por fases):**

1. Hermosillo, Sonora (MVP)
2. Estado de Sonora completo
3. Zona Norte de México
4. Centro y Sur de México

**Modelo de acceso:**

* Dashboards: 100% público, sin login
* Chatbot: funcional sin login (historial se pierde al recargar)
* Chatbot con historial: requiere Google OAuth 2.0
* No se almacenan contraseñas nunca

## 2. Arquitectura del Sistema

### 2.1 Stack Tecnológico

| Capa          | Actual (MVP)           | Futuro (Producción)              |
| ------------- | ---------------------- | --------------------------------- |
| Backend       | FastAPI (Python 3.12+) | FastAPI + Celery (jobs)           |
| Frontend      | HTML/CSS/JS + Jinja2   | React SPA (Liquid Glass UI)       |
| Base de Datos | SQLite local           | PostgreSQL (remoto)               |
| ORM           | SQLAlchemy             | SQLAlchemy (sin cambios)          |
| LLM           | Ollama API (Qwen 3.5)  | Ollama cloud / Anthropic / Google |
| Vector DB     | —                     | pgvector o ChromaDB               |
| Mapas         | Leaflet.js             | Leaflet.js                        |
| Scheduling    | Manual                 | Cron jobs / APScheduler           |
| Paquetes      | uv                     | uv                                |

### 2.2 Patrón Arquitectónico

```
┌─────────────────────────────────────────────┐
│ USUARIO (navegador)                         │
└──────────────┬──────────────┬───────────────┘
               │              │
        Dashboard         Chatbot
               ▼              ▼
┌──────────────────────┐ ┌──────────────────────┐
│ React SPA            │ │ Chat UI              │
│ (Liquid Glass)       │ │ (mismo SPA)          │
└──────────┬───────────┘ └──────────┬───────────┘
           │                        │
           ▼                        ▼
┌─────────────────────────────────────────────┐
│ 		FastAPI Backend               │
└─────────────────────────────────────────────┘

┌─────────────┐	┌─────────────┐ ┌─────────────┐
|   /api/v1   | |   /api/v1   | |   /api/v1   |
|   gasolina  | |    gas-lp   | |  qqp/super  |
└───────┬─────┘ └───────┬─────┘ └───────┬─────┘
	|		|		|   
        ▼		▼		▼
┌─────────────────────────────────────────────┐
│ 		 SQLAlchemy ORM 	      |
|          Repository Pattern + Cache         │
└───────────────────────┬─────────────────────┘
			|
			▼
┌─────────────────────────────────────────────┐
│		SQLite / PostgreSQL	      |
└─────────────────────────────────────────────┘
```

### 2.3 Estrategia de Datos (Caching Inteligente)

| Categoría  | Frecuencia        | Trigger                                  |
| ----------- | ----------------- | ---------------------------------------- |
| Gasolina    | Diaria (AM)       | Usuario busca + datos > 24h              |
| Gas LP      | Semanal (sábado) | Usuario busca +datos > último sábado |
| QQP/super   | Bimensual         | Manual o schedule (PROFECO publica)      |
| Ubicaciones | Una vez           | Scraping inicial, luego solo updates     |

**Regla general:**

Si el usuario busca un lugar y los datos están vigentes → se sirve de caché

Si están vencidos → se llama la del API gobierno → guardar en db → responder al usuario

**Manejo de datos inexistentes:**

* Si un municipio no tiene datos para una categoría, mostrar: "De momento no tenemos datos de [categoría] para [municipio]. Estamos trabajando para ampliar la cobertura."
* Las opciones de Estado/Municipio en los selectores se filtran
  dinámicamente según la categoría seleccionada.

## 3. Estado Actual del Proyecto

### 3.1 Módulos

| Módulo             | Estado | Funcional | Producción | Notas                           |
| ------------------- | ------ | --------- | ----------- | ------------------------------- |
| Pipeline Gasolina   | ✅     | ✅        | ⚠️        | Falta schedule automático      |
| UI Gasolina         | ✅     | ✅        | ⚠️        | Falta responsive, filtros extra |
| Scraper ubicaciones | ✅     | ✅        | ⚠️        | No ejecutado, se corre 1 vez    |
| Pipeline Gas LP     | ✅     | ✅        | ⚠️        | Falta schedule automático      |
| UI Gas LP           | ✅     | ✅        | ⚠️        | Falta comparador proveedores    |
| Pipeline QQP        | ✅     | ✅        | ⚠️        | Falta schedule automático      |
| UI Supermercados    | ❌     | —        | —          | No existe aún                  |
| Annotator           | ✅     | ✅        | ⚠️        | Funcional para crops + metadata |
| OAuth               | ❌     | —        | —          | Fase 2+                         |
| Chatbot             | ❌     | —        | —          | Fase 4                          |
| React SPA           | ❌     | —        | —          | Fase 2                          |
| Scheduling          | ❌     | —        | —          | Fase 1 Pendiente                |

---

### 3.2 Pendientes críticos de fase 1

- [ ] Ejecutar scraper de ubicaciones de gasolineras (código existe)
- [ ] Implementar scheduler automático (APScheduler o cron) horario México centro:
  - Gasolina: diario 6:00 AM
  - Gas LP: sábados 8:00 AM
  - QQP: 1ro y 15 de cada mes (o manual)
- [ ] Validar schemas de datos para las 3 categorías
- [ ] Definir qué estados/municipios cubre QQP realmente
- [ ] Migrar de SQLite a PostgreSQL (para producción)

---

## 4. Fases de Desarrollo

### FASE 1: Estabilización de Pipelines (Actual)

**Objetivo:** Que los 3 pipelines corran solos sin intervención manual.

#### Infraestructura

#### 1.1 Gasolina

- [ ] Ejecutar scraper de ubicaciones (una vez)
- [ ] Schedule diario de actualización de precios
- [ ] Validar que el cache de 24h funciona correctamente
- [ ] Log de errores si la API del CRE falla
- [ ] Fallback: servir datos vencidos con aviso al usuario

#### 1.2 Gas LP

- [ ] Schedule semanal (sábados)
- [ ] Validar expiración basada en último sábado
- [ ] Log de errores si la API del CNE falla
- [ ] Fallback: servir datos vencidos con aviso al usuario

#### 1.3 QQP / Supermercados

- [ ] Mapear cobertura real (¿qué estados/municipios tiene?)
- [ ] Schedule bimensual o trigger manual
- [ ] Normalizar nombres de productos (mayúsculas, acentos, etc.)
- [ ] Deduplicar productos similares

#### 1.4 Infraestructura

- [ ] APScheduler integrado en FastAPI lifespan
- [ ] Logging unificado (archivo + consola)
- [ ] Health check endpoint: GET /api/v1/health

```
{
  "gasolina": {"ultima_actualizacion": "2025-01-15", "vigente": true},
  "gas_lp": {"ultima_actualizacion": "2025-01-11", "vigente": true},
  "qqp": {"ultima_actualizacion": "2024-12-01", "vigente": false}
}
```

### FASE 2: SPA + Liquid Glass UI

**Objetivo:** Unificar la experiencia en una sola aplicación React moderna.

#### 2.1 Decisión técnica: ¿Por qué React?

| Vanilla JS (actual)               | React (propuesto)                      |
| --------------------------------- | -------------------------------------- |
| Sin dependencias                  | Ecosistema maduro de componentes       |
| Difícil mantener estado complejo | Estado centralizado (useState/Context) |
| DOM manipulation manual           | Virtual DOM eficiente                  |
| Difícil hacer SPA                | SPA nativo con React Router            |
| OK para páginas simples          | Necesario para chatbot + dashboards    |

****Setup propuesto:** Vite + React + React Router
**CSS:** Tailwind CSS (utility-first, perfecto para Liquid Glass)**

#### 2.2 Estructura de la SPA

```
/                     → Landing page (hero + resumen de las 3 categorías)
/gasolina             → Dashboard de gasolina (mapa + filtros + ranking)
/gas-lp               → Dashboard de gas LP (comparador + tabla)
/supermercados        → Dashboard de precios QQP (tabla + filtros)
/chat                 → Chatbot (Fase 4, placeholder por ahora)
```

#### 2.3 Diseño UI: Liquid Glass

**Principios:**

* Tema light (no dark)
* Fondo: gradientes suaves (blues, purples)
* Tarjetas: efecto glassmorphism (backdrop-filter: blur)
* Transiciones smooth (300ms ease)
* Responsive: mobile-first
* Performance: lazy loading, code splitting por ruta

**Componentes Liquid Glass reutilizables:**

```
<GlassCard>        → Contenedor principal con blur
<GlassButton>      → Botón con efecto glass
<GlassNavbar>      → Navbar fija translúcida
<GlassSelect>      → Dropdown estilizado
<GlassModal>       → Modal con overlay blur
<GlassKPI>         → Tarjeta de indicador numérico
```

#### 2.4 Vista Landing Page ("/")

```
┌─────────────────────────────────────────────┐
│  [GLASS NAVBAR]  SINA  | Gas | GasLP | Super│
├─────────────────────────────────────────────┤
│                                             │
│    ╔═══════════════════════════════════╗    │
│    ║  SINA                             ║    │
│    ║                                   ║    │
│    ║  [Explorar precios]               ║    │
│    ╚═══════════════════════════════════╝    │
│                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │  Gas     │ │  GasLP   │ │   Super  │     │
│  │ $XX.XX   │ │ $XX.XX   │ │ XXX prod │     │
│  │ promedio │ │ promedio │ │ en oferta│     │
│  └──────────┘ └──────────┘ └──────────┘     │
│                                             │
│  "Datos actualizados al DD/MM/YYYY"         │
└─────────────────────────────────────────────┘
```

#### 2.5 Vista Gasolina ("/gasolina") — REFACTORIZAR

**Ya existe, migrar a React:**

* Mapa Leaflet con marcadores color-coded
* Autocomplete de estado/municipio
* Tabla ranking de precios
* Migrar a componente React
* Agregar filtro por tipo combustible (Regular, Premium, Diésel)
* Agregar gráfica de tendencia (si hay histórico)
* Responsive mobile
* Indicador visual de "datos vigentes" vs "datos vencidos"

#### 2.6 Vista Gas LP ("/gas-lp") — REFACTORIZAR

**Ya existe, migrar a React:**

* Selectores estado → municipio → localidad (cascada)
* Tabla de precios por proveedor
* Migrar a componente React
* Comparador visual entre proveedores
* Mapa con cobertura (si hay coordenadas)
* Badge "Mejor precio" en el más barato

#### 2.7 Vista Supermercados ("/supermercados") — NUEVA

```
┌────────────────────────────────────────────────┐
│  Filtros: [Estado ▼] [Municipio ▼] [Producto]  │
│           [Categoría ▼] [Tienda ▼]             │
├────────────────────────────────────────────────┤
│  Producto    │ Tienda A  │ Tienda B │ Tienda C │
│  Leche 1L    │ $22.50    │ $24.00   │ $21.90 ★ │
│  Aceite 1L   │ $35.00 ★ │ $38.50    │ $36.00  │
│  Arroz 1kg   │ \$18.00    │ $17.50 ★│ $19.00  │
├────────────────────────────────────────────────┤
│  ★ = Precio más bajo                           │
│  Datos de PROFECO, actualizados al DD/MM/YYYY  │
└────────────────────────────────────────────────┘
```

#### 2.8 Google OAuth 2.0

* Botón "Iniciar sesión con Google" en navbar
* Sin login: todo funcional, sin persistencia
* Con login: historial de chat guardado en DB
* Tabla usuarios: google_id, email, nombre, created_at
* Tabla chat_historial: user_id, mensaje, respuesta, timestamp

### FASE 3: Motor de Búsqueda Vectorial y RAG

**Objetivo:** Preparar la infraestructura semántica para el chatbot.

#### 3.1 ¿Qué se vectoriza?

| Entidad          | Texto a vectorizar                      | Metadata                              |
| ---------------- | --------------------------------------- | ------------------------------------- |
| Gasolinera       | "{marca} en {dirección}, {municipio}"  | lat, lng, estado, municipio, precios  |
| Proveedor Gas LP | "{empresa} en {localidad}, {municipio}" | estado, municipio, precios            |
| Producto QQP     | "{producto} {marca} {presentación}"    | tienda, precio, municipio, categoría |

#### 3.2 Stack vectorial

* **Opción A:** pgvector (extensión de PostgreSQL) → menos infra
* **Opción B:** ChromaDB (standalone) → más flexible

#### 3.3 Criterios de éxito

* Búsqueda "leche más barata en Hermosillo" retorna top 5 en < 2s
* Búsqueda "gasolinera cerca de [coordenadas]" retorna top 3 con distancia
* Precision > 80% en queries de productos

### FASE 4: Chatbot Agéntico

**Objetivo:** Asistente conversacional que resuelve consultas de ahorro.

#### 4.1 Queries que DEBE poder responder

**Gasolina:**

* "¿Dónde está la gasolina más barata cerca de mí?"
* "¿Cuánto cuesta la premium en Hermosillo?"
* "¿Qué gasolinera me recomiendas en [colonia/zona]?"

**Gas LP:**

* "¿Cuánto cuesta el gas LP esta semana?"
* "¿Qué proveedor es más barato en [localidad]?"
* "¿Cuándo se actualizan los precios del gas?"

**Supermercados:**

* "¿Dónde está más barata la leche?"
* "Tengo esta lista: [productos]. ¿En qué tienda me sale más barato?"
* "¿Qué ofertas hay esta semana en Ley?"

**General:**

* "¿Cuánto me puedo ahorrar si cambio de gasolinera?"
* "¿Qué es PROFECO?"
* "No entiendo, explícame más sencillo" (accesibilidad)

#### 4.2 Flujo del agente

```
Usuario: "¿Dónde compro más barata la leche en Hermosillo?"
              │
              ▼
┌─────────────────────────────┐
│  LLM Router (Intent)        │
│  → Detecta: buscar_producto │
│  → Params: leche, Hermosillo│
└──────────────┬──────────────┘
               ▼
┌──────────────────────────────┐
│  Tool: buscar_producto()     │
│  1. Filtro duro: QQP DB      │
│     WHERE municipio = Hillo  │
│     AND producto LIKE leche  │
│  2. Ordena por precio ASC    │
│  3. Retorna top 5 JSON       │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  LLM Genera respuesta:       │
│  "La leche más barata está   │
│   en Soriana Centro a $21.90 │
│   seguida de Walmart..."     │
└──────────────────────────────┘
```

#### 4.3 Manejo de ubicación

* Si el usuario permite geolocalización → usar coordenadas
* Si no → preguntar: "¿En qué municipio te encuentras?"
* Guardar en sesión para no preguntar repetidamente

#### 4.4 Proveedor LLM (abstracción)

```
# ABC para cambiar proveedor fácilmente
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, context: dict) -> str: ...

class OllamaProvider(LLMProvider): ...    # Actual
class AnthropicProvider(LLMProvider): ...  # Futuro
class GoogleProvider(LLMProvider): ...     # Futuro
```

### FASE 5: Annotator + ML Pipeline (Largo Plazo)

**Objetivo:** Automatizar extracción de datos de folletos de supermercados.

#### 5.1 Roadmap de supermercados

| Prioridad | Supermercado | Método flyer | Estado       |
| --------- | ------------ | ------------- | ------------ |
| 1         | Casa Ley     | Web scraping  | ✅ Funcional |
| 2         | Abarrey      | Web scraping  | ❌ Pendiente |
| 3         | Soriana      | Web scraping  | ❌ Pendiente |
| 4         | Walmart      | Web scraping  | ❌ Pendiente |

#### 5.2 Pipeline ML

```
Flyer imagen → Roboflow (detección zonas) → Recortes → 
LLM (extracción texto) → JSON estructurado → DB
```


* Acumular dataset de annotator (mínimo ~500 imágenes anotadas)
* Entrenar modelo en Roboflow (object detection)
* Integrar modelo en pipeline automatizado
* Eliminar necesidad de anotación manual

#### 5.3 Expansión geográfica flyers

1. Hermosillo
2. Sonora (estado completo)
3. Zona Norte
4. Centro y Sur México

## 5. Esquema de Base de Datos

### Tablas actuales (funcionando)

| Tabla           | Propósito                             |
| --------------- | -------------------------------------- |
| gasolineras     | Precios + ubicaciones de gasolineras   |
| gas_lp_precios  | Precios Gas LP por proveedor/localidad |
| qqp_precios     | Precios productos PROFECO              |
| cne_entidades   | Catálogo de estados                   |
| cne_municipios  | Catálogo de municipios                |
| cne_localidades | Catálogo de localidades               |

### Tablas nuevas (Fase 2+)

| Tabla          | Propósito                        | Fase |
| -------------- | --------------------------------- | ---- |
| usuarios       | Google OAuth users                | 2    |
| chat_historial | Conversaciones del chatbot        | 4    |
| favoritos      | Gasolineras/productos guardados   | 2    |
| alertas        | "Avísame si baja de $X" (futuro) | 3+   |

---

## 6. Criterios de "Listo para Producción"

### Para presentar al municipio necesitas:

* Los 3 dashboards funcionando en la SPA
* Datos actualizándose automáticamente
* UI profesional (Liquid Glass)
* Funcione en celular (responsive)
* Deployed en un servidor público (Railway, Render, o VPS)
* Dominio propio (ej. sina.mx)
* Página "Acerca de" con propósito del proyecto
* Métricas básicas: cuántos usuarios, consultas por día

### Nice to have para la presentación:

* Chatbot funcional
* Demo en vivo con datos reales
* Comparación: "Un usuario puede ahorrar $X al mes usando SINA"
