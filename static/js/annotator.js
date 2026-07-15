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
let TREE = {};                 // árbol de datos/ (se carga vía API con la clave)
let activeLabel = 'zona';
let activeColor = '#7a2492';
let boundingBoxes = [];
let boxCounter = 0;

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
        alert('Árbol cargado. Selecciona supermercado, ciudad, fecha e imagen.');
    } catch (e) {
        console.error(e);
        alert('No se pudo cargar el árbol. Revisa la clave de administrador.');
    }
}

// ==========================================
// 1. SCRAPER
// ==========================================
function downloadFlyer() {
    const store = document.getElementById('scrapeStore').value;
    const city = document.getElementById('scrapeCity').value;
    if (!city.trim()) { alert('Por favor, ingresa una ciudad.'); return; }

    const btn = document.getElementById('btnScrape');
    btn.disabled = true;
    btn.innerHTML = '⏳ Extrayendo...';

    fetch('/api/v1/annotator/flyer', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ supermarket: store, city: city }),
    })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(() => { alert(`Folleto de ${store} en ${city} descargado. Recarga el árbol.`); cargarArbol(); })
        .catch(err => { console.error(err); alert('Error al descargar el folleto.'); })
        .finally(() => { btn.disabled = false; btn.innerHTML = '📥 Descargar Ahora'; });
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
    btn.innerText = '⏳ Verificando...'; btn.disabled = true;
    try {
        const r = await fetch(
            `/api/v1/annotator/status?supermarket=${store}&city=${city}&date=${date}`,
            { headers: authHeaders() });
        const s = await r.json();
        btn.disabled = false;
        if (s.has_recortes) { btn.innerText = 'Extraer por zona (VLM)'; }
        else { btn.innerText = '⚠️ Recorta zonas primero'; btn.disabled = true; }
    } catch (err) {
        console.error(err); btn.innerText = 'Extraer por zona (VLM)'; btn.disabled = false;
    }
}

imageSelect.addEventListener('change', (e) => {
    const filename = e.target.value;
    if (!filename) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
    document.getElementById('placeholder').style.display = 'none';
    const store = storeSelect.value, city = citySelect.value, date = dateSelect.value;
    currentImg.src = `/datos/${store}/${city}/${date}/${filename}`;
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
    activeLabel = label; activeColor = color;
    document.querySelectorAll('.class-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.class === label);
    });
}

function imgCoords(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
        scaleX, scaleY,
    };
}

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
});

canvas.addEventListener('mousemove', (e) => {
    if (currentTool === 'pan' && isPanning) {
        canvasArea.scrollLeft = startScrollLeft - (e.clientX - startPanX);
        canvasArea.scrollTop = startScrollTop - (e.clientY - startPanY);
        return;
    }
    if (!mode) return;
    const c = imgCoords(e);

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
});

canvas.addEventListener('mouseup', (e) => {
    if (currentTool === 'pan') { isPanning = false; canvas.style.cursor = 'grab'; return; }
    if (mode === 'draw') {
        const c = imgCoords(e);
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
    if (mode === 'move' || mode === 'resize') updateAnnotationList();
    else if (mode === 'draw') updateAnnotationList();
    mode = null; activeIndex = -1;
    redrawCanvas();
});

canvas.addEventListener('mouseleave', () => {
    if (isPanning) { isPanning = false; canvas.style.cursor = 'grab'; }
    mode = null; activeIndex = -1;
});

function redrawCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (currentImg.src) ctx.drawImage(currentImg, 0, 0, canvas.width, canvas.height);
    boundingBoxes.forEach(box => {
        ctx.strokeStyle = box.color; ctx.lineWidth = 3;
        ctx.strokeRect(box.x, box.y, box.w, box.h);
        // Manija de redimensión (esquina inferior derecha).
        ctx.fillStyle = box.color;
        ctx.fillRect(box.x + box.w - 8, box.y + box.h - 8, 16, 16);
        // Etiqueta.
        ctx.fillRect(box.x, box.y - 20, ctx.measureText(box.label).width + 10, 20);
        ctx.fillStyle = '#000'; ctx.font = '14px Arial';
        ctx.fillText(box.label, box.x + 5, box.y - 5);
    });
}

// ==========================================
// 5. PRE-ANOTACIÓN (CV clásico)
// ==========================================
async function preanotar() {
    const store = storeSelect.value, city = citySelect.value,
        date = dateSelect.value, filename = imageSelect.value;
    if (!filename) { alert('Selecciona una imagen primero.'); return; }
    const btn = document.getElementById('btnPreanotar');
    btn.disabled = true; btn.innerText = '⏳ Detectando zonas...';
    try {
        const r = await fetch('/api/v1/annotator/preanotar', {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ supermarket: store, city, date, image_name: filename }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status);
        boundingBoxes = (data.zonas || []).map(z => {
            boxCounter++;
            return { id: boxCounter, label: 'zona', color: activeColor, x: z.x, y: z.y, w: z.w, h: z.h };
        });
        updateAnnotationList(); redrawCanvas();
    } catch (e) {
        console.error(e); alert('Error en pre-anotación: ' + e.message);
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
        const item = document.createElement('div');
        item.className = 'annot-item';
        item.innerHTML = `
            <div class="annot-label">
                <span class="color-dot" style="background-color:${box.color}"></span>
                ${box.label} [${box.w}x${box.h}]
            </div>
            <button class="delete-btn" onclick="deleteBox(${index})">❌</button>`;
        annotList.appendChild(item);
    });
}

function deleteBox(index) { boundingBoxes.splice(index, 1); updateAnnotationList(); redrawCanvas(); }
function clearAll() { boundingBoxes = []; updateAnnotationList(); redrawCanvas(); }

function saveAll() {
    if (boundingBoxes.length === 0) { alert('Dibuja o pre-anota al menos una zona.'); return; }
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
            alert(`Guardado. ${data.data.crops_saved} recortes generados.`);
            checkProcessingStatus(store, city, date);
        })
        .catch(err => { console.error(err); alert('Error al guardar las zonas.'); });
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
    if (!store || !city || !date) { alert('Selecciona supermercado, ciudad y fecha.'); return; }

    const btn = document.getElementById('btnExtract');
    btn.innerText = '⏳ Procesando VLM...'; btn.disabled = true;
    const cont = document.getElementById('zonasReview');
    cont.innerHTML = 'Extrayendo zonas con el VLM (puede tardar)...';
    openModal();

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
            <button class="btn btn-outline" onclick="agregarFila(this)">+ Fila</button>
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
        <td><button class="delete-btn" onclick="this.closest('tr').remove()">❌</button></td>
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
    if (productos.length === 0) { alert('No hay productos con nombre para insertar.'); return; }

    const btn = document.getElementById('btnInsertar');
    btn.disabled = true; btn.innerText = '⏳ Insertando...';
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
        alert(`Insertados/actualizados: ${data.insertados} productos.`);
        closeModal();
    } catch (e) {
        console.error(e); alert('Error al insertar: ' + e.message);
    } finally {
        btn.disabled = false; btn.innerText = 'Verificar e insertar a la base de datos';
    }
}
