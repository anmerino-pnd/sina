/**
 * SINA Annotator - Frontend Logic
 *
 * Flujo: conectar (clave admin) -> elegir imagen -> Pre-anotar zonas (CV) o
 * dibujar -> ajustar (mover/redimensionar) -> Guardar (recortes + dataset YOLO)
 * -> Extraer por zona (VLM) -> revisar/editar -> Verificar e insertar a Postgres.
 */

// --- DOM Elements ---
const canvas = document.getElementById('annotCanvas');
const ctx = canvas.getContext('2d');
const annotList = document.getElementById('annotationList');
const canvasArea = document.getElementById('canvasArea');

const storeSelect = document.getElementById('storeSelect');
const citySelect = document.getElementById('citySelect');
const dateSelect = document.getElementById('dateSelect');
const imageSelect = document.getElementById('imageSelect');

// --- State ---
let currentImg = new Image();
// Ícono X de línea (sin emojis; coherente con CSP estricta: es markup, no script).
const ICON_X = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>';
// Color de las cajas en el canvas: verde salvia (acorde a la paleta, legible).
const ZONE_COLOR = '#2f9e86';
let TREE = {};                 // árbol de datos/ (se carga vía API con la clave)
let activeLabel = 'zona';
let activeColor = ZONE_COLOR;
let boundingBoxes = [];
let boxCounter = 0;
let hoverIndex = -1;           // zona resaltada desde la lista lateral

// ==========================================
// NOTIFICACIONES EN PÁGINA (sin popups nativos del navegador)
// ==========================================
function notify(msg, type = 'info', ms = 3800) {
    const stack = document.getElementById('toast');
    if (!stack) return;
    const t = document.createElement('div');
    t.className = 'toast toast-' + type;
    t.textContent = msg;
    stack.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => {
        t.classList.remove('show');
        setTimeout(() => t.remove(), 280);
    }, ms);
}

// ==========================================
// TEMA claro/oscuro — sincronizado con la SPA vía localStorage["sina.theme"]
// (default oscuro para este espacio de trabajo; el usuario lo alterna)
// ==========================================
const THEME_KEY = 'sina.theme';
const ICON_SUN = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const ICON_MOON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

function temaActual() {
    const v = localStorage.getItem(THEME_KEY);
    if (v === 'dark' || v === 'light') return v;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}
function aplicarTema(t) {
    document.documentElement.classList.toggle('light', t === 'light');
    const btn = document.getElementById('btnTheme');
    if (btn) btn.innerHTML = (t === 'light') ? ICON_MOON : ICON_SUN;
}
function alternarTema() {
    const t = document.documentElement.classList.contains('light') ? 'dark' : 'light';
    localStorage.setItem(THEME_KEY, t);
    aplicarTema(t);
}
aplicarTema(temaActual());   // aplica de inmediato (reduce parpadeo)

// ==========================================
// DROPDOWN PROPIO (el <select> nativo no se puede estilizar).
// Mantiene el <select> real como fuente de verdad (oculto) y sincroniza una UI
// a medida; así el resto del código sigue usando .value / .add() / change.
// ==========================================
const CHEVRON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
let csActiveClose = null;

function enhanceSelect(sel) {
    sel.classList.add('cs-native');
    const wrap = document.createElement('div');
    wrap.className = 'cs';
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel);

    const control = document.createElement('button');
    control.type = 'button';
    control.className = 'cs-control';
    control.setAttribute('aria-haspopup', 'listbox');
    control.setAttribute('aria-expanded', 'false');
    control.innerHTML = '<span class="cs-value"></span>' + CHEVRON;
    wrap.appendChild(control);

    const valueEl = control.querySelector('.cs-value');
    let panel = null;

    // Cierra al hacer scroll FUERA del panel (dejar hacer scroll dentro de listas largas).
    function onDocScroll(e) {
        if (panel && e.target instanceof Node && panel.contains(e.target)) return;
        close();
    }

    function refresh() {
        const o = sel.options[sel.selectedIndex];
        valueEl.textContent = o ? o.textContent : '';
        wrap.classList.toggle('is-disabled', sel.disabled);
    }
    function close() {
        if (panel) { panel.remove(); panel = null; }
        control.setAttribute('aria-expanded', 'false');
        document.removeEventListener('scroll', onDocScroll, true);
        window.removeEventListener('resize', close);
        csActiveClose = null;
    }
    function open() {
        if (panel || sel.disabled) return;
        if (csActiveClose) csActiveClose();
        panel = document.createElement('div');
        panel.className = 'cs-panel';
        Array.from(sel.options).forEach((o, i) => {
            const opt = document.createElement('div');
            opt.className = 'cs-option'
                + (i === sel.selectedIndex ? ' is-selected' : '')
                + (o.disabled ? ' is-disabled' : '');
            opt.textContent = o.textContent;
            if (!o.disabled) {
                opt.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    sel.value = o.value;
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                    refresh();
                    close();
                });
            }
            panel.appendChild(opt);
        });
        const r = control.getBoundingClientRect();
        panel.style.left = r.left + 'px';
        panel.style.top = (r.bottom + 6) + 'px';
        panel.style.width = r.width + 'px';
        document.body.appendChild(panel);
        control.setAttribute('aria-expanded', 'true');
        csActiveClose = close;
        document.addEventListener('scroll', onDocScroll, true);
        window.addEventListener('resize', close);
    }

    control.addEventListener('click', (e) => {
        e.stopPropagation();
        panel ? close() : open();
    });
    sel.addEventListener('change', refresh);
    new MutationObserver(refresh).observe(sel, {
        childList: true, attributes: true, attributeFilter: ['disabled'],
    });
    refresh();
}

// Interacción con cajas (dibujar / mover / redimensionar)
let mode = null;               // 'draw' | 'move' | 'resize' | null
let activeIndex = -1;
let startX = 0, startY = 0;
let dragOffX = 0, dragOffY = 0;
const HANDLE = 12;             // px (en pantalla) de la esquina de redimensión

// Herramienta y paneo
let currentTool = 'draw';
let isPanning = false;
let startPanX = 0, startPanY = 0, startScrollLeft = 0, startScrollTop = 0;

// Zoom
let zoomLevel = 1.0;
const MIN_ZOOM = 0.2, MAX_ZOOM = 4.0;

// ==========================================
// 0. AUTENTICACIÓN (X-Admin-Key en cada fetch)
// ==========================================
function getKey() { return sessionStorage.getItem('sina.adminKey') || ''; }

function authHeaders() {
    const h = { 'Content-Type': 'application/json' };
    const k = getKey();
    if (k) h['X-Admin-Key'] = k;
    return h;
}

async function cargarArbol() {
    const key = document.getElementById('adminKey').value.trim();
    if (key) sessionStorage.setItem('sina.adminKey', key);
    try {
        const resp = await fetch('/api/v1/annotator/tree', { headers: authHeaders() });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        TREE = data.tree || {};
        storeSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
        Object.keys(TREE).forEach(store => {
            storeSelect.add(new Option(store.toUpperCase().replace(/_/g, ' '), store));
        });
        notify('Árbol cargado. Selecciona supermercado, ciudad, fecha e imagen.', 'ok');
        cargarPendientes();
    } catch (e) {
        console.error(e);
        notify('No se pudo cargar el árbol. Revisa la clave de administrador.', 'error');
    }
}

// ==========================================
// 0.b PANEL "FOLLETOS": ciclo de vida por tienda-ciudad
// ==========================================
const ETAPA_LABEL = { descargado: 'Descargado', anotado: 'Anotado', extraido: 'Extraído', persistido: 'Persistido', vacio: 'Vacío' };
const ACCION_LABEL = {
    'anotar': 'Anotar zonas',
    'extraer': 'Extraer con VLM',
    'insertar': 'Insertar a la base',
    'capturar vigencia': 'Capturar vigencia al insertar',
    'esperando flyer nuevo': 'Esperando folleto nuevo',
    'al dia': 'Al día',
    'sin imagenes': 'Sin imágenes',
};

async function cargarPendientes() {
    const cont = document.getElementById('pendientesList');
    if (!cont) return;
    try {
        const r = await fetch('/api/v1/annotator/pendientes', { headers: authHeaders() });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();
        renderPendientes(data.pendientes || []);
    } catch (e) {
        console.error(e);
        cont.innerHTML = '<p class="pend-empty">No se pudo consultar el estado de los folletos.</p>';
    }
}

function renderPendientes(items) {
    const cont = document.getElementById('pendientesList');
    const countEl = document.getElementById('pendCount');
    const atencion = items.filter(i => i.accion !== 'al dia');
    if (countEl) countEl.textContent = String(atencion.length);

    if (items.length === 0) {
        cont.innerHTML = '<p class="pend-empty">Sin folletos descargados todavía.</p>';
        return;
    }

    cont.innerHTML = items.map(i => {
        const titulo = `${i.tienda} · ${i.ciudad}`.toUpperCase().replace(/_/g, ' ');
        const etapa = i.etapa === 'anotado' && i.anotadas < i.imagenes
            ? `Anotado ${i.anotadas}/${i.imagenes}`
            : (ETAPA_LABEL[i.etapa] || i.etapa);
        const vig = i.vigencia_fin ? `vence ${esc(i.vigencia_fin)}` : 'vigencia sin capturar';
        const chips = `<span class="chip">${esc(etapa)}</span>`
            + (i.vencido === true ? '<span class="chip chip-warn">Vencido</span>' : '');
        return `<button type="button" class="pend-item${i.accion === 'al dia' ? ' is-ok' : ''}"
                    data-store="${esc(i.tienda)}" data-city="${esc(i.ciudad)}" data-date="${esc(i.fecha)}">
                <span class="pend-title">${esc(titulo)}</span>
                <span class="pend-meta">${esc(i.fecha)} · ${vig}</span>
                <span class="pend-chips">${chips}</span>
                <span class="pend-accion">${esc(ACCION_LABEL[i.accion] || i.accion)}</span>
            </button>`;
    }).join('');

    if (atencion.length > 0) {
        notify(`${atencion.length} folleto(s) requieren atención.`, 'info');
    }
}

// Fija un valor en un <select> disparando 'change' (cascada + dropdown propio).
function seleccionar(sel, value) {
    if (!Array.from(sel.options).some(o => o.value === value)) return false;
    sel.value = value;
    sel.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
}

function irAFlyer(store, city, date) {
    if (seleccionar(storeSelect, store) && seleccionar(citySelect, city) && seleccionar(dateSelect, date)) {
        notify('Folleto seleccionado. Elige una imagen para trabajar.', 'info');
    }
}

// ==========================================
// 1. SCRAPER
// ==========================================
// Resuelve la ciudad elegida: del select, o del campo "añadir otra" si aplica.
function ciudadSeleccionada() {
    const sel = document.getElementById('scrapeCity');
    if (sel.value === '__add__') {
        return document.getElementById('scrapeCityNew').value.trim();
    }
    return sel.value.trim();
}

function downloadFlyer() {
    const store = document.getElementById('scrapeStore').value;
    const city = ciudadSeleccionada();
    if (!city) { notify('Elige o escribe una ciudad.', 'error'); return; }

    const btn = document.getElementById('btnScrape');
    btn.disabled = true;
    btn.textContent = 'Descargando…';

    fetch('/api/v1/annotator/flyer', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ supermarket: store, city: city }),
    })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(() => { notify(`Folleto de ${store} en ${city} descargado.`, 'ok'); cargarArbol(); })
        .catch(err => { console.error(err); notify('Error al descargar el folleto.', 'error'); })
        .finally(() => { btn.disabled = false; btn.textContent = 'Descargar ahora'; });
}

// ==========================================
// 2. ZOOM & HERRAMIENTA
// ==========================================
function setTool(tool) {
    currentTool = tool;
    const btnDraw = document.getElementById('btnDraw');
    const btnPan = document.getElementById('btnPan');
    if (tool === 'draw') {
        canvas.style.cursor = 'crosshair';
        btnDraw.classList.add('active'); btnPan.classList.remove('active');
    } else {
        canvas.style.cursor = 'grab';
        btnPan.classList.add('active'); btnDraw.classList.remove('active');
    }
}

function changeZoom(delta) { setZoom(zoomLevel + delta); }
function resetZoom() { setZoom(1.0); }
function setZoom(newZoom) {
    if (!currentImg.src) return;
    zoomLevel = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));
    document.getElementById('zoomLabel').innerText = `${Math.round(zoomLevel * 100)}%`;
    canvas.style.width = `${currentImg.width * zoomLevel}px`;
    canvas.style.height = `${currentImg.height * zoomLevel}px`;
}

canvasArea.addEventListener('wheel', (e) => {
    if (e.ctrlKey) { e.preventDefault(); changeZoom(e.deltaY > 0 ? -0.1 : 0.1); }
}, { passive: false });

// ==========================================
// 3. DROPDOWNS (usa TREE cargado por API)
// ==========================================
storeSelect.addEventListener('change', (e) => {
    citySelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    dateSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    imageSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    citySelect.disabled = !e.target.value;
    dateSelect.disabled = true; imageSelect.disabled = true;
    if (e.target.value) {
        Object.keys(TREE[e.target.value] || {}).forEach(city => {
            citySelect.add(new Option(city.toUpperCase().replace(/_/g, ' '), city));
        });
    }
});

citySelect.addEventListener('change', (e) => {
    dateSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    imageSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    dateSelect.disabled = !e.target.value; imageSelect.disabled = true;
    const store = storeSelect.value;
    if (e.target.value) {
        const dates = Object.keys(TREE[store][e.target.value] || {});
        dates.sort((a, b) => b.localeCompare(a));
        dates.slice(0, 10).forEach(d => dateSelect.add(new Option(d, d)));
    }
});

dateSelect.addEventListener('change', (e) => {
    imageSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    imageSelect.disabled = !e.target.value;
    const store = storeSelect.value, city = citySelect.value, date = e.target.value;
    if (date) {
        (TREE[store][city][date] || []).forEach(file => {
            if (/\.(jpg|jpeg|png)$/i.test(file)) imageSelect.add(new Option(file, file));
        });
        checkProcessingStatus(store, city, date);
    }
});

async function checkProcessingStatus(store, city, date) {
    const btn = document.getElementById('btnExtract');
    btn.innerText = 'Verificando…'; btn.disabled = true;
    try {
        const r = await fetch(
            `/api/v1/annotator/status?supermarket=${store}&city=${city}&date=${date}`,
            { headers: authHeaders() });
        const s = await r.json();
        btn.disabled = false;
        if (s.has_recortes) { btn.innerText = 'Extraer por zona (VLM)'; }
        else { btn.innerText = 'Recorta zonas primero'; btn.disabled = true; }
    } catch (err) {
        console.error(err); btn.innerText = 'Extraer por zona (VLM)'; btn.disabled = false;
    }
}

imageSelect.addEventListener('change', (e) => {
    const filename = e.target.value;
    if (!filename) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
    document.getElementById('placeholder').style.display = 'none';
    const store = storeSelect.value, city = citySelect.value, date = dateSelect.value;
    currentImg.src = `/datos/flyers/${store}/${city}/${date}/${filename}`;
    currentImg.onload = () => {
        canvas.width = currentImg.width;
        canvas.height = currentImg.height;
        resetZoom();
        boundingBoxes = [];
        updateAnnotationList();
        redrawCanvas();
        canvasArea.scrollLeft = 0; canvasArea.scrollTop = 0;
    };
});

// ==========================================
// 4. CANVAS: dibujar / mover / redimensionar
// ==========================================
function setActiveClass(label, color) {
    activeLabel = label; activeColor = ZONE_COLOR;   // color fijo de zona (no morado)
    document.querySelectorAll('.class-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.class === label);
    });
}

function imgCoordsFromClient(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (clientX - rect.left) * scaleX,
        y: (clientY - rect.top) * scaleY,
        scaleX, scaleY,
    };
}
function imgCoords(e) { return imgCoordsFromClient(e.clientX, e.clientY); }

function hitTest(x, y, scaleX) {
    // Devuelve {index, corner} para la caja superior bajo el cursor.
    const h = HANDLE * scaleX;
    for (let i = boundingBoxes.length - 1; i >= 0; i--) {
        const b = boundingBoxes[i];
        const enEsquina = Math.abs(x - (b.x + b.w)) <= h && Math.abs(y - (b.y + b.h)) <= h;
        if (enEsquina) return { index: i, corner: true };
        if (x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) return { index: i, corner: false };
    }
    return { index: -1, corner: false };
}

// Aplica el arrastre en curso (dibujar / mover / redimensionar) para la posición dada.
// Se separa de los listeners para poder reusarla desde el auto-scroll de bordes.
function processDrag(clientX, clientY) {
    if (!mode) return;
    const c = imgCoordsFromClient(clientX, clientY);
    if (mode === 'move') {
        const b = boundingBoxes[activeIndex];
        b.x = Math.max(0, Math.min(canvas.width - b.w, Math.round(c.x - dragOffX)));
        b.y = Math.max(0, Math.min(canvas.height - b.h, Math.round(c.y - dragOffY)));
        redrawCanvas();
    } else if (mode === 'resize') {
        const b = boundingBoxes[activeIndex];
        b.w = Math.max(10, Math.round(c.x - b.x));
        b.h = Math.max(10, Math.round(c.y - b.y));
        redrawCanvas();
    } else if (mode === 'draw') {
        redrawCanvas();
        ctx.strokeStyle = activeColor; ctx.lineWidth = 3;
        ctx.strokeRect(startX, startY, c.x - startX, c.y - startY);
    }
}

// Auto-scroll al arrastrar cerca de los bordes del área: permite dibujar/mover
// zonas MÁS GRANDES que el área visible sin tener que alejar el zoom.
let lastClient = { x: 0, y: 0 };
let autoScrollRAF = null;
const EDGE = 56;          // margen (px) desde el borde que dispara el desplazamiento
const EDGE_SPEED = 24;    // velocidad máx. de desplazamiento (px por frame)

function autoScrollTick() {
    if (!mode) { autoScrollRAF = null; return; }
    const r = canvasArea.getBoundingClientRect();
    let dx = 0, dy = 0;
    if (lastClient.x < r.left + EDGE)        dx = -EDGE_SPEED * Math.min(1, (r.left + EDGE - lastClient.x) / EDGE);
    else if (lastClient.x > r.right - EDGE)  dx =  EDGE_SPEED * Math.min(1, (lastClient.x - (r.right - EDGE)) / EDGE);
    if (lastClient.y < r.top + EDGE)         dy = -EDGE_SPEED * Math.min(1, (r.top + EDGE - lastClient.y) / EDGE);
    else if (lastClient.y > r.bottom - EDGE) dy =  EDGE_SPEED * Math.min(1, (lastClient.y - (r.bottom - EDGE)) / EDGE);
    if (dx || dy) {
        canvasArea.scrollLeft += dx;
        canvasArea.scrollTop += dy;
        processDrag(lastClient.x, lastClient.y);   // recomputa coords tras desplazar
    }
    autoScrollRAF = requestAnimationFrame(autoScrollTick);
}
function startAutoScroll() { if (autoScrollRAF == null) autoScrollRAF = requestAnimationFrame(autoScrollTick); }
function stopAutoScroll() { if (autoScrollRAF != null) { cancelAnimationFrame(autoScrollRAF); autoScrollRAF = null; } }

canvas.addEventListener('mousedown', (e) => {
    if (!currentImg.src) return;
    if (currentTool === 'pan') {
        isPanning = true; canvas.style.cursor = 'grabbing';
        startPanX = e.clientX; startPanY = e.clientY;
        startScrollLeft = canvasArea.scrollLeft; startScrollTop = canvasArea.scrollTop;
        return;
    }
    const c = imgCoords(e);
    const hit = hitTest(c.x, c.y, c.scaleX);
    if (hit.index >= 0 && hit.corner) {
        mode = 'resize'; activeIndex = hit.index;
    } else if (hit.index >= 0) {
        mode = 'move'; activeIndex = hit.index;
        dragOffX = c.x - boundingBoxes[hit.index].x;
        dragOffY = c.y - boundingBoxes[hit.index].y;
    } else {
        mode = 'draw'; startX = c.x; startY = c.y;
    }
    lastClient = { x: e.clientX, y: e.clientY };
    startAutoScroll();
    e.preventDefault();
});

// Movimiento y soltar en `window`: el arrastre sigue aunque el cursor salga del canvas.
window.addEventListener('mousemove', (e) => {
    if (currentTool === 'pan' && isPanning) {
        canvasArea.scrollLeft = startScrollLeft - (e.clientX - startPanX);
        canvasArea.scrollTop = startScrollTop - (e.clientY - startPanY);
        return;
    }
    if (!mode) return;
    lastClient = { x: e.clientX, y: e.clientY };
    processDrag(e.clientX, e.clientY);
});

window.addEventListener('mouseup', (e) => {
    if (currentTool === 'pan') { isPanning = false; canvas.style.cursor = 'grab'; return; }
    if (!mode) return;
    if (mode === 'draw') {
        const c = imgCoordsFromClient(e.clientX, e.clientY);
        const x = Math.min(startX, c.x), y = Math.min(startY, c.y);
        const w = Math.abs(c.x - startX), h = Math.abs(c.y - startY);
        if (w > 10 && h > 10) {
            boxCounter++;
            boundingBoxes.push({
                id: boxCounter, label: activeLabel, color: activeColor,
                x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h),
            });
        }
    }
    updateAnnotationList();
    mode = null; activeIndex = -1;
    stopAutoScroll();
    redrawCanvas();
});

function hexToRgba(hex, a) {
    const h = (hex || '#7a2492').replace('#', '');
    const full = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    const n = parseInt(full, 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

function redrawCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (currentImg.src) ctx.drawImage(currentImg, 0, 0, canvas.width, canvas.height);
    // Escala trazos/etiquetas al tamaño real de la imagen (flyers grandes).
    const S = Math.max(1, canvas.width / 1200);
    const hs = Math.round(7 * S);            // media-arista de la manija
    const fpx = Math.round(15 * S);          // tamaño de fuente del número
    ctx.font = `700 ${fpx}px "Segoe UI", system-ui, sans-serif`;
    ctx.textBaseline = 'alphabetic';
    boundingBoxes.forEach((box, index) => {
        const activo = (index === hoverIndex || index === activeIndex);
        // Relleno translúcido (más marcado si está resaltada desde la lista o en edición).
        ctx.fillStyle = hexToRgba(box.color, activo ? 0.30 : 0.12);
        ctx.fillRect(box.x, box.y, box.w, box.h);
        ctx.strokeStyle = box.color; ctx.lineWidth = (activo ? 4 : 2) * S;
        ctx.strokeRect(box.x, box.y, box.w, box.h);
        // Manija de redimensión (esquina inferior derecha) con contorno claro.
        ctx.fillStyle = box.color;
        ctx.fillRect(box.x + box.w - hs, box.y + box.h - hs, hs * 2, hs * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.92)'; ctx.lineWidth = Math.max(1, 1.5 * S);
        ctx.strokeRect(box.x + box.w - hs, box.y + box.h - hs, hs * 2, hs * 2);
        // Número de zona (identificación) en un chip.
        const etiqueta = String(index + 1);
        const pad = Math.round(6 * S);
        const chipH = fpx + pad;
        const tw = ctx.measureText(etiqueta).width + pad * 2;
        ctx.fillStyle = box.color;
        ctx.fillRect(box.x, box.y - chipH, tw, chipH);
        ctx.fillStyle = '#07211f';
        ctx.fillText(etiqueta, box.x + pad, box.y - pad);
    });
}

// ==========================================
// 5. PRE-ANOTACIÓN (CV clásico)
// ==========================================
async function preanotar() {
    const store = storeSelect.value, city = citySelect.value,
        date = dateSelect.value, filename = imageSelect.value;
    if (!filename) { notify('Selecciona una imagen primero.', 'error'); return; }
    const btn = document.getElementById('btnPreanotar');
    btn.disabled = true; btn.innerText = 'Detectando zonas…';
    try {
        const fusionEl = document.getElementById('fusionSelect');
        const fusion = fusionEl ? parseFloat(fusionEl.value) || 0 : 0;
        const r = await fetch('/api/v1/annotator/preanotar', {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ supermarket: store, city, date, image_name: filename, fusion }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status);
        boundingBoxes = (data.zonas || []).map(z => {
            boxCounter++;
            return { id: boxCounter, label: 'zona', color: activeColor, x: z.x, y: z.y, w: z.w, h: z.h };
        });
        updateAnnotationList(); redrawCanvas();
        notify(`${boundingBoxes.length} zona(s) propuesta(s). Ajústalas y guarda.`, 'ok');
    } catch (e) {
        console.error(e); notify('Error en pre-anotación: ' + e.message, 'error');
    } finally {
        btn.disabled = false; btn.innerText = 'Pre-anotar zonas (CV)';
    }
}

// ==========================================
// 6. LISTA / GUARDAR
// ==========================================
function updateAnnotationList() {
    annotList.innerHTML = '';
    document.getElementById('annotCount').innerText = boundingBoxes.length;
    boundingBoxes.forEach((box, index) => {
        const n = index + 1;
        const item = document.createElement('div');
        item.className = 'annot-item';
        item.dataset.index = index;
        item.innerHTML = `
            <div class="annot-label">
                <span class="zone-num">${n}</span>
                <span class="annot-dims">${box.w} × ${box.h} px</span>
            </div>
            <button class="delete-btn" data-action="del-box" data-index="${index}" aria-label="Eliminar zona ${n}" title="Eliminar zona ${n}">${ICON_X}</button>`;
        annotList.appendChild(item);
    });
}

function deleteBox(index) { boundingBoxes.splice(index, 1); updateAnnotationList(); redrawCanvas(); }
function clearAll() { boundingBoxes = []; updateAnnotationList(); redrawCanvas(); }

function saveAll() {
    if (boundingBoxes.length === 0) { notify('Dibuja o pre-anota al menos una zona.', 'error'); return; }
    const store = storeSelect.value, city = citySelect.value,
        date = dateSelect.value, filename = imageSelect.value;
    if (!filename) return;

    fetch('/api/v1/annotator/annotate', {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({
            supermarket: store, city, date, image_name: filename, bboxes: boundingBoxes,
        }),
    })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(data => {
            notify(`Guardado. ${data.data.crops_saved} recortes generados.`, 'ok');
            checkProcessingStatus(store, city, date);
        })
        .catch(err => { console.error(err); notify('Error al guardar las zonas.', 'error'); });
}

// ==========================================
// 7. EXTRACCIÓN POR ZONA (VLM) + REVISIÓN + INSERCIÓN
// ==========================================
function openModal() { document.getElementById('jsonModal').style.display = 'flex'; }
function closeModal() { document.getElementById('jsonModal').style.display = 'none'; }

function esc(s) {
    return String(s == null ? '' : s)
        .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

async function extractData() {
    const store = storeSelect.value, city = citySelect.value, date = dateSelect.value;
    if (!store || !city || !date) { notify('Selecciona supermercado, ciudad y fecha.', 'error'); return; }

    const btn = document.getElementById('btnExtract');
    btn.innerText = 'Procesando…'; btn.disabled = true;
    const cont = document.getElementById('zonasReview');
    cont.innerHTML = 'Extrayendo zonas con el VLM (puede tardar)...';
    openModal();
    precargarVigencia(store, city, date);

    try {
        const r = await fetch('/api/v1/annotator/extract', {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ supermarket: store, city, date }),
        });
        const result = await r.json();
        if (!r.ok) throw new Error(result.detail || 'Error del servidor');
        renderZonas(result.data);
    } catch (e) {
        console.error(e);
        cont.innerHTML = `<p style="color:#ff5555;">Error: ${esc(e.message)}</p>`;
    } finally {
        btn.innerText = 'Extraer por zona (VLM)'; btn.disabled = false;
    }
}

// Precarga la vigencia en el modal desde metadata.json (la escribe el spider si
// la tienda la publica en su sitio, p.ej. Abarrey). Si no hay, se captura a mano
// (en Casa Ley viene impresa en la imagen). Los campos siempre son editables.
async function precargarVigencia(store, city, date) {
    const vi = document.getElementById('vigInicio');
    const vf = document.getElementById('vigFin');
    const nota = document.getElementById('vigNota');
    vi.value = ''; vf.value = '';
    try {
        const r = await fetch(`/datos/flyers/${store}/${city}/${date}/metadata.json`);
        if (r.ok) {
            const md = await r.json();
            if (md.vigencia_inicio && md.vigencia_fin) {
                vi.value = md.vigencia_inicio;
                vf.value = md.vigencia_fin;
                if (nota) nota.textContent = 'Vigencia leída del sitio de la tienda — verifícala antes de insertar.';
                return;
            }
        }
    } catch (e) { console.error(e); }
    if (nota) nota.textContent = 'Vigencia no disponible: captúrala del folleto (viene impresa en la imagen).';
}

function renderZonas(data) {
    const cont = document.getElementById('zonasReview');
    const zonas = (data && data.zonas) || {};
    const nombres = Object.keys(zonas);
    if (nombres.length === 0) { cont.innerHTML = '<p>No se encontraron zonas/productos.</p>'; return; }

    let html = `<p style="margin:10px 0;"><strong>Total productos:</strong> ${data.total_productos || 0}. `
        + `Revisa y corrige antes de insertar.</p>`;
    nombres.forEach(nombre => {
        const z = zonas[nombre];
        const flag = z.revisar ? ' <span style="color:#ffb86c;">(revisar)</span>' : '';
        html += `<details open style="margin-bottom:12px;">
            <summary><strong>${esc(nombre)}</strong> — ${z.n || 0} producto(s)${flag}</summary>
            <table class="professional-table" data-zone="${esc(nombre)}">
                <thead><tr><th>Producto</th><th>Marca</th><th>Precio</th><th>Unidad</th><th>Promo</th><th></th></tr></thead>
                <tbody>`;
        (z.productos || []).forEach(p => {
            html += filaProducto(p);
        });
        html += `</tbody></table>
            <button class="btn btn-outline" data-action="add-row">+ Fila</button>
            </details>`;
    });
    cont.innerHTML = html;
}

function filaProducto(p) {
    p = p || {};
    return `<tr>
        <td><input class="p-nombre" value="${esc(p.producto)}"></td>
        <td><input class="p-marca" value="${esc(p.marca)}"></td>
        <td><input class="p-precio" type="number" step="0.01" value="${p.precio == null ? '' : esc(p.precio)}"></td>
        <td><input class="p-unidad" value="${esc(p.unidad)}"></td>
        <td><input class="p-promo" value="${esc(p.tipo_oferta)}"></td>
        <td><button class="delete-btn" data-action="del-row" aria-label="Eliminar" title="Eliminar">${ICON_X}</button></td>
    </tr>`;
}

function agregarFila(btn) {
    const tbody = btn.previousElementSibling.querySelector('tbody');
    tbody.insertAdjacentHTML('beforeend', filaProducto({}));
}

async function insertarProductos() {
    const store = storeSelect.value, city = citySelect.value, date = dateSelect.value;
    const productos = [];
    document.querySelectorAll('#zonasReview tbody tr').forEach(tr => {
        const nombre = tr.querySelector('.p-nombre')?.value.trim();
        if (!nombre) return;
        const precioRaw = tr.querySelector('.p-precio')?.value;
        productos.push({
            producto: nombre,
            marca: tr.querySelector('.p-marca')?.value.trim() || null,
            precio: precioRaw ? parseFloat(precioRaw) : null,
            unidad: tr.querySelector('.p-unidad')?.value.trim() || null,
            tipo_oferta: tr.querySelector('.p-promo')?.value.trim() || null,
        });
    });
    if (productos.length === 0) { notify('No hay productos con nombre para insertar.', 'error'); return; }

    const btn = document.getElementById('btnInsertar');
    btn.disabled = true; btn.innerText = 'Insertando…';
    try {
        const r = await fetch('/api/v1/annotator/persistir', {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({
                supermarket: store, city, date,
                tienda: storeSelect.options[storeSelect.selectedIndex].text,
                fuente: 'flyer',
                vigencia_inicio: document.getElementById('vigInicio').value || null,
                vigencia_fin: document.getElementById('vigFin').value || null,
                productos,
            }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status);
        notify(`Insertados/actualizados: ${data.insertados} productos.`, 'ok');
        closeModal();
    } catch (e) {
        console.error(e); notify('Error al insertar: ' + e.message, 'error');
    } finally {
        btn.disabled = false; btn.innerText = 'Verificar e insertar a la base de datos';
    }
}

// ==========================================
// 8. CABLEADO (CSP estricta: sin onclick inline; todo por addEventListener)
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const on = (id, fn) => { const el = document.getElementById(id); if (el) el.addEventListener('click', fn); };

    aplicarTema(temaActual());          // reafirma el ícono una vez que existe el botón
    on('btnTheme', alternarTema);

    // Dropdown propio para cada <select> (no para inputs de texto/fecha).
    document.querySelectorAll('select.select').forEach(enhanceSelect);
    // Cerrar el panel abierto al hacer clic fuera o con Escape.
    document.addEventListener('click', () => { if (csActiveClose) csActiveClose(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && csActiveClose) csActiveClose(); });

    on('btnCargarArbol', cargarArbol);
    on('btnScrape', downloadFlyer);
    on('btnDraw', () => setTool('draw'));
    on('btnPan', () => setTool('pan'));
    on('btnPreanotar', preanotar);
    on('btnZoomOut', () => changeZoom(-0.1));
    on('btnZoomIn', () => changeZoom(0.1));
    on('btnZoomReset', resetZoom);
    on('btnExtract', extractData);
    on('btnSaveAll', saveAll);
    on('btnClearAll', clearAll);
    on('btnCloseModal', closeModal);
    on('btnInsertar', insertarProductos);

    // Clase activa (los botones vienen del loop Jinja).
    document.querySelectorAll('.class-btn').forEach(b => {
        b.addEventListener('click', () => setActiveClass(b.dataset.class, b.dataset.color));
    });

    // "Obtener nuevo folleto": mostrar el campo de nueva ciudad al elegir "Añadir otra…".
    const scrapeCity = document.getElementById('scrapeCity');
    const scrapeCityNew = document.getElementById('scrapeCityNew');
    if (scrapeCity && scrapeCityNew) {
        scrapeCity.addEventListener('change', () => {
            const add = scrapeCity.value === '__add__';
            scrapeCityNew.style.display = add ? 'block' : 'none';
            if (add) scrapeCityNew.focus();
        });
    }

    // Delegación para contenido generado dinámicamente (innerHTML).
    annotList.addEventListener('click', (e) => {
        const del = e.target.closest('[data-action="del-box"]');
        if (del) deleteBox(Number(del.dataset.index));
    });
    // Resaltar en el canvas la zona sobre la que se pasa el mouse en la lista.
    annotList.addEventListener('mouseover', (e) => {
        const item = e.target.closest('.annot-item');
        if (!item) return;
        const idx = Number(item.dataset.index);
        if (idx !== hoverIndex) { hoverIndex = idx; redrawCanvas(); }
    });
    annotList.addEventListener('mouseleave', () => {
        if (hoverIndex !== -1) { hoverIndex = -1; redrawCanvas(); }
    });
    const zonasReview = document.getElementById('zonasReview');
    if (zonasReview) zonasReview.addEventListener('click', (e) => {
        const add = e.target.closest('[data-action="add-row"]');
        if (add) { agregarFila(add); return; }
        const del = e.target.closest('[data-action="del-row"]');
        if (del) { del.closest('tr').remove(); }
    });

    // Panel "Folletos": clic en una fila → preselecciona tienda/ciudad/fecha.
    const pendList = document.getElementById('pendientesList');
    if (pendList) pendList.addEventListener('click', (e) => {
        const item = e.target.closest('.pend-item');
        if (item) irAFlyer(item.dataset.store, item.dataset.city, item.dataset.date);
    });
});
