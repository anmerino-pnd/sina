var datos        = [];
var combustible  = 'Magna';
var estadoSel    = '';
var munSel       = '';
var map          = null;
var mLayer       = null;
var mapInit      = false;
var markersRef   = [];
var markerSelIdx = -1;
var userMarker   = null;
var userCircle   = null;
var userLoc      = null;          // {lat, lng} — GPS o manual
var modoFijar    = false;         // modo para clic manual en mapa
var pinManual    = null;          // marker del punto fijado manualmente
var catFiltro = null; // null = todas, 'Barato', 'Promedio', 'Caro'
var zoomAntes = null; // zoom antes de seleccionar un marker

// ─────────────────────────────────────────────
//  AUTOCOMPLETE ESTADO
// ─────────────────────────────────────────────
function filtrarEstados() {
    var q  = document.getElementById('inp-estado').value.toLowerCase().trim();
    var ks = Object.keys(CATALOGO).sort();
    var f  = q ? ks.filter(function(k){ return k.toLowerCase().indexOf(q) !== -1; }) : ks;
    renderDrop('drop-estado', f, false, seleccionarEstado);
}

function seleccionarEstado(val) {
    estadoSel = val;
    munSel    = '';
    document.getElementById('inp-estado').value       = cap(val);
    document.getElementById('inp-municipio').value    = '';
    document.getElementById('inp-municipio').disabled = false;
    document.getElementById('btn-ver').disabled       = true;
    cerrarDrop('estado');
}

// ─────────────────────────────────────────────
//  AUTOCOMPLETE MUNICIPIO
// ─────────────────────────────────────────────
function filtrarMunicipios() {
    if (!estadoSel) return;
    var q    = document.getElementById('inp-municipio').value.toLowerCase().trim();
    var muns = CATALOGO[estadoSel] || [];
    var f    = q ? muns.filter(function(m){ return m.toLowerCase().indexOf(q) !== -1; }) : muns;
    renderDrop('drop-municipio', f, true, seleccionarMunicipio);
}

function seleccionarMunicipio(val) {
    munSel = val;
    document.getElementById('inp-municipio').value = cap(val);
    document.getElementById('btn-ver').disabled    = false;
    cerrarDrop('municipio');
}

// ─────────────────────────────────────────────
//  DROPDOWN
// ─────────────────────────────────────────────
function renderDrop(id, items, badge, cb) {
    var drop = document.getElementById(id);
    drop.innerHTML = '';

    if (items.length === 0) {
        drop.innerHTML = '<div class="drop-empty">Sin resultados</div>';
        drop.classList.add('open');
        return;
    }

    items.forEach(function(item) {
        var div  = document.createElement('div');
        div.className = 'drop-item';

        var span = document.createElement('span');
        span.textContent = cap(item);
        div.appendChild(span);

        div.addEventListener('mousedown', function(e){ e.preventDefault(); cb(item); });
        drop.appendChild(div);
    });

    drop.classList.add('open');
}

function abrirDrop(t) {
    if (t === 'estado')    filtrarEstados();
    if (t === 'municipio') filtrarMunicipios();
}

function cerrarDrop(t) {
    document.getElementById('drop-' + t).classList.remove('open');
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('#wrap-estado'))    cerrarDrop('estado');
    if (!e.target.closest('#wrap-municipio')) cerrarDrop('municipio');
});

// ─────────────────────────────────────────────
//  CARGAR CIUDAD
// ─────────────────────────────────────────────
async function cargarCiudad() {
    if (!estadoSel || !munSel) return;

    document.getElementById('sc-welcome').style.display = 'none';
    document.getElementById('sc-prox').style.display    = 'none';
    document.getElementById('dashboard').style.display  = 'none';

    try {
        const res = await fetch(
            `/sina/gasolina/db?estado=${encodeURIComponent(estadoSel)}&municipio=${encodeURIComponent(munSel)}`

        );

        if (!res.ok) {
            document.getElementById('prox-txt').innerHTML =
                `No hay datos para <strong>${cap(munSel)}, ${cap(estadoSel)}</strong>.`;
            document.getElementById('sc-prox').style.display = 'flex';
            return;
        }

        const json = await res.json();
        datos = json.datos.filter(r => {
            const lat = parseFloat(r.latitud);
            const lng = parseFloat(r.longitud);
            return !isNaN(lat) && !isNaN(lng);
        }).map(r => ({
            Nombre:    r.nombre    || '',
            Direccion: r.direccion || '',
            Numero:    r.numero    || '',
            Magna:     r.magna   != null ? parseFloat(r.magna)   : null,
            Premium:   r.premium != null ? parseFloat(r.premium) : null,
            Diesel:    r.diesel  != null ? parseFloat(r.diesel)  : null,
            Latitud:   parseFloat(r.latitud),
            Longitud:  parseFloat(r.longitud),
        }));

        combustible  = 'Magna';
        markerSelIdx = -1;
        syncPills();
        detectarCombustibles();

        document.getElementById('dashboard').style.display = 'block';
        document.getElementById('nav-right').textContent   =
            cap(munSel) + ', ' + cap(estadoSel);

        resetDetalle();
        if (modoFijar) toggleModoFijar();
        initMapa();
        render();

    } catch (e) {
        console.error(e);
        alert('Error al cargar datos. Intenta de nuevo.');
    }
}

// ─────────────────────────────────────────────
//  RENDER COMPLETO
// ─────────────────────────────────────────────
function render() {
    renderKPIs();
    renderMapa();
    renderRanking();
}

// ─────────────────────────────────────────────
//  KPIs
// ─────────────────────────────────────────────
function renderKPIs() {
    var ps = [];
    for (var i = 0; i < datos.length; i++) {
        var v = datos[i][combustible];
        if (v !== null && !isNaN(v)) ps.push(v);
    }

    txt('sec-label',   'Precios de ' + combustible + ' · ' + cap(munSel));
    txt('mapa-titulo', 'Gasolineras · ' + combustible);
    txt('rank-titulo', '🏆 Top 10 más baratas · ' + combustible);

    if (ps.length === 0) {
        txt('kpi-prom','--'); txt('kpi-min','--'); txt('kpi-max','--'); txt('kpi-est','0');
        return;
    }

    var s = 0, mn = ps[0], mx = ps[0];
    for (var j = 0; j < ps.length; j++) {
        s += ps[j];
        if (ps[j] < mn) mn = ps[j];
        if (ps[j] > mx) mx = ps[j];
    }

    txt('kpi-prom', '$' + (s/ps.length).toFixed(2));
    txt('kpi-min',  '$' + mn.toFixed(2));
    txt('kpi-max',  '$' + mx.toFixed(2));
    txt('kpi-est',  '' + ps.length);
}

// ─────────────────────────────────────────────
//  MAPA: inicializar
// ─────────────────────────────────────────────
function initMapa() {
    if (mapInit) { mLayer.clearLayers(); return; }

    map = L.map('map', { 
        zoomControl: true,
        center: [23.6345, -102.5528],
        zoom: 5
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    mLayer = L.layerGroup().addTo(map);

    // 👇 Un solo listener que maneja ambos casos
    map.on('click', function(e) {
        if (modoFijar) {
            // Modo fijar activo → clavar pin
            fijarUbicacionManual(e.latlng.lat, e.latlng.lng);
        } else {
            // Click normal en mapa vacío → deseleccionar
            deseleccionarMarker();
        }
    });

    mapInit = true;
}

function deseleccionarMarker() {
    // Restaurar marker anterior
    if (markerSelIdx !== -1 && markersRef[markerSelIdx]) {
        var p = markersRef[markerSelIdx];
        p.m.setIcon(mkPunto(p.color, false));
        p.m.setZIndexOffset(0);
        p.m.closeTooltip();
    }
    markerSelIdx = -1;

    // Cerrar todos los tooltips
    markersRef.forEach(function(ref) { ref.m.closeTooltip(); });

    // Zoom out suave (2 niveles menos, mínimo zoom 11)
    var zoomActual = map.getZoom();
    var zoomNuevo  = Math.max(zoomActual - 2, 11);
    map.setZoom(zoomNuevo, { animate: true, duration: 0.4 });

    // Reset detalle
    resetDetalle();
}

// ─────────────────────────────────────────────
//  MAPA: renderizar puntos
// ─────────────────────────────────────────────
function renderMapa() {
    mLayer.clearLayers();
    markersRef   = [];
    markerSelIdx = -1;

    var cp = [];
    for (var i = 0; i < datos.length; i++) {
        var d = datos[i];
        if (d[combustible] !== null && !isNaN(d[combustible])) cp.push(d);
    }

    if (cp.length === 0) return;

    var ps   = cp.map(function(d){ return d[combustible]; });
    var lats = cp.map(function(d){ return d.Latitud; });
    var lngs = cp.map(function(d){ return d.Longitud; });

    if (lats.length === 0 || lngs.length === 0) {
        console.warn('Sin coordenadas válidas para centrar el mapa.');
        return;
    }

    map.fitBounds(
        L.latLngBounds(
            [Math.min.apply(null,lats), Math.min.apply(null,lngs)],
            [Math.max.apply(null,lats), Math.max.apply(null,lngs)]
        ),
        { padding: [28,28] }
    );

    cp.forEach(function(d, idx) {
        var precio = d[combustible];
        var cat    = categorizar(precio, ps);
        var color  = getColor(cat);

        var m = L.marker([d.Latitud, d.Longitud], {
            icon: mkPunto(color, false),
            title: d.Nombre
        });

        m._myColor = color;
        m._myIdx   = idx;

        m.on('click', function(){
            selMarker(idx);
            mostrarDetalle(d, precio, ps);
        });

        m.bindTooltip(
            '<strong>' + esc(d.Nombre) + '</strong><br>' +
            combustible + ': <strong>$' + precio.toFixed(2) + '</strong><br>' +
            '<span style="color:' + color + '">● ' + cat + '</span>',
            { direction: 'top', offset: [0, -7] }
        );

        mLayer.addLayer(m);
        markersRef.push({ 
            m     : m, 
            d     : d, 
            color : color, 
            precio: precio,
            numero: d.Numero
        });
    });
}

// ─────────────────────────────────────────────
//  MARCADOR PUNTO
// ─────────────────────────────────────────────
function mkPunto(color, sel) {
    var sz = sel ? 30 : 15;
    var bw = sel ? 3  : 2;
    var sh = sel
        ? '0 0 0 5px ' + color + '35, 0 2px 8px rgba(0,0,0,0.28)'
        : '0 1px 3px rgba(0,0,0,0.22)';
    var a = sz / 2;

    return L.divIcon({
        html: '<div style="width:' + sz + 'px;height:' + sz + 'px;' +
              'background:' + color + ';border-radius:50%;' +
              'border:' + bw + 'px solid white;box-shadow:' + sh + ';' +
              'transition:all 0.15s"></div>',
        className: '', iconSize: [sz,sz], iconAnchor: [a,a], popupAnchor: [0,-a]
    });
}

// ─────────────────────────────────────────────
//  SELECCIONAR MARKER
// ─────────────────────────────────────────────
function selMarker(idx) {
    if (markerSelIdx !== -1 && markersRef[markerSelIdx]) {
        var p = markersRef[markerSelIdx];
        p.m.setIcon(mkPunto(p.color, false));
        p.m.setZIndexOffset(0);
    }
    markerSelIdx = idx;
    if (idx !== -1 && markersRef[idx]) {
        var s = markersRef[idx];
        s.m.setIcon(mkPunto(s.color, true));
        s.m.setZIndexOffset(999);
        map.setView([s.d.Latitud, s.d.Longitud], 15, { animate: true, duration: 0.5 });
        s.m.openTooltip();
    }
}

// ─────────────────────────────────────────────
//  MOSTRAR DETALLE (desktop + inline)
// ─────────────────────────────────────────────
function mostrarDetalle(d, precio, todosPrecios) {
    var cat  = precio != null ? categorizar(precio, todosPrecios) : '—';
    var dist = userLoc ? ' · ' + distKm(userLoc.lat, userLoc.lng, d.Latitud, d.Longitud).toFixed(1) + ' km' : '';
    var meta = combustible + ' · ' + cat + dist;

    // Desktop (columna 3)
    document.getElementById('detail-ph').style.display      = 'none';
    document.getElementById('detail-content').style.display = 'block';
    document.getElementById('detail-card').classList.add('filled');
    txt('d-nombre', d.Nombre || '—');
    txt('d-dir',    d.Direccion || 'Sin dirección registrada');
    txt('d-meta',   meta);
    setDV('d-magna',   d.Magna);
    setDV('d-premium', d.Premium);
    setDV('d-diesel',  d.Diesel);

    // Inline (tablet/móvil)
    document.getElementById('detail-inline').classList.add('visible');
    txt('di-nombre', d.Nombre || '—');
    txt('di-dir',    d.Direccion || 'Sin dirección registrada');
    txt('di-meta',   meta);
    setDVId('di-magna',   d.Magna);
    setDVId('di-premium', d.Premium);
    setDVId('di-diesel',  d.Diesel);
}

function setDV(id, val) {
    var el = document.getElementById(id);
    if (val !== null && !isNaN(parseFloat(val))) {
        el.textContent = '$' + parseFloat(val).toFixed(2);
        el.className   = 'dp-val';
    } else {
        el.textContent = 'N/D';
        el.className   = 'dp-val na';
    }
}

function setDVId(id, val) { setDV(id, val); }

function resetDetalle() {
    document.getElementById('detail-ph').style.display      = 'flex';
    document.getElementById('detail-content').style.display = 'none';
    document.getElementById('detail-card').classList.remove('filled');
    document.getElementById('detail-inline').classList.remove('visible');
}

// ─────────────────────────────────────────────
//  RANKING
// ─────────────────────────────────────────────
function renderRanking() {
    var lista = [];
    for (var i = 0; i < datos.length; i++) {
        var v = datos[i][combustible];
        if (v !== null && !isNaN(v)) lista.push({ d: datos[i], precio: v });
    }

    lista.sort(function(a,b){ return a.precio - b.precio; });

    var ps    = lista.map(function(x){ return x.precio; });
    var top10 = lista.slice(0,10);
    var tbody = document.getElementById('rank-body');

    if (top10.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#ccc;padding:18px">Sin datos</td></tr>';
        return;
    }

    var html = '';
    for (var j = 0; j < top10.length; j++) {
        var item = top10[j];
        var cat  = categorizar(item.precio, ps);
        var bCl  = cat === 'Barato' ? 'b-b' : (cat === 'Promedio' ? 'b-p' : 'b-c');
        var pCl  = cat === 'Barato' ? 'p-b' : (cat === 'Promedio' ? 'p-p' : 'p-c');
        var nom  = item.d.Nombre.length > 20 ? item.d.Nombre.slice(0,18) + '…' : item.d.Nombre;

        html += '<tr data-j="' + j + '">' +
            '<td style="color:#c7c7cc;font-weight:600">' + (j+1) + '</td>' +
            '<td style="font-weight:500">' + esc(nom) + '</td>' +
            '<td class="' + pCl + '">$' + item.precio.toFixed(2) + '</td>' +
            '<td><span class="badge ' + bCl + '">' + cat + '</span></td>' +
            '</tr>';
    }

    tbody.innerHTML = html;

    var rows = tbody.querySelectorAll('tr');
    for (var k = 0; k < rows.length; k++) {
        (function(idx) {
            rows[idx].addEventListener('click', function() {
                var item = top10[idx];

                // Highlight fila
                var all = tbody.querySelectorAll('tr');
                for (var r = 0; r < all.length; r++) all[r].classList.remove('sel');
                rows[idx].classList.add('sel');

                // Detalle
                mostrarDetalle(item.d, item.precio, ps);

                // Marker en mapa
                for (var m = 0; m < markersRef.length; m++) {
                    var ref = markersRef[m];
                    if (ref.numero === item.d.Numero) {
                        selMarker(m);
                        break;
                    }
                }
            });
        })(k);
    }
}

// ─────────────────────────────────────────────
//  MI UBICACIÓN (GPS automático)
// ─────────────────────────────────────────────
function ubicarme() {
    if (!navigator.geolocation) {
        alert('Tu navegador no soporta geolocalización.');
        return;
    }

    var btn = document.getElementById('mbtn-ubicame');
    btn.textContent = '⌛ Buscando...';
    btn.disabled    = true;

    navigator.geolocation.getCurrentPosition(
        function(pos) {
            btn.textContent = '📍 Mi ubicación';
            btn.disabled    = false;
            aplicarUbicacion(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy || 80, false);
        },
        function() {
            btn.textContent = '📍 Mi ubicación';
            btn.disabled    = false;
            alert('No se pudo obtener tu ubicación. Usa "Fijar punto" para colocarla manualmente.');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
}

// ─────────────────────────────────────────────
//  MODO FIJAR PUNTO MANUAL
// ─────────────────────────────────────────────
function toggleModoFijar() {
    modoFijar = !modoFijar;

    var btnFijar  = document.getElementById('mbtn-fijar');
    var hint      = document.getElementById('map-hint');
    var mapEl     = document.getElementById('map');

    if (modoFijar) {
        btnFijar.classList.add('active');
        btnFijar.textContent = '✓ Haz clic en el mapa';
        hint.classList.add('visible');
        mapEl.classList.add('map-pin-mode');
    } else {
        btnFijar.classList.remove('active');
        btnFijar.textContent = '📌 Fijar punto';
        hint.classList.remove('visible');
        mapEl.classList.remove('map-pin-mode');
    }
}

function fijarUbicacionManual(lat, lng) {
    // Desactivar modo
    modoFijar = false;
    var btnFijar = document.getElementById('mbtn-fijar');
    btnFijar.classList.remove('active');
    btnFijar.textContent = '📌 Fijar punto';
    document.getElementById('map-hint').classList.remove('visible');
    document.getElementById('map').classList.remove('map-pin-mode');

    aplicarUbicacion(lat, lng, 0, true);
}

function aplicarUbicacion(lat, lng, accuracy, esManual) {
    userLoc = { lat: lat, lng: lng };

    if (userMarker) map.removeLayer(userMarker);
    if (userCircle) map.removeLayer(userCircle);
    if (pinManual)  map.removeLayer(pinManual);

    if (!esManual && accuracy > 0) {
        userCircle = L.circle([lat, lng], {
            radius: accuracy,
            color: '#0071e3',
            fillColor: '#0071e3',
            fillOpacity: 0.07,
            weight: 1
        }).addTo(map);
    }

    if (esManual) {
        pinManual = L.circleMarker([lat, lng], {
            radius:      10,
            color:       'white',
            weight:      3,
            fillColor:   '#1d1d1f',
            fillOpacity: 1
        }).addTo(map);

        pinManual.bindTooltip('Tu punto de referencia').openTooltip();

        if (window.radioManual) map.removeLayer(window.radioManual);
        window.radioManual = L.circle([lat, lng], {
            radius:      2000,
            color:       '#1d1d1f',
            weight:      1.5,
            dashArray:   '6 4',
            fillColor:   '#1d1d1f',
            fillOpacity: 0.04
        }).addTo(map);
    } else {
        // Punto azul GPS
        userMarker = L.circleMarker([lat, lng], {
            radius: 8, color: 'white', weight: 3,
            fillColor: '#0071e3', fillOpacity: 1
        }).addTo(map);
        userMarker.bindTooltip('Tu ubicación').openTooltip();
    }

    // Mostrar botón "Quitar punto"
    document.getElementById('mbtn-quitar').style.display = 'inline-block';

    map.setView([lat, lng], 14, { animate: true, duration: 0.6 });

    renderCercanas();
}

function quitarUbicacion() {
    userLoc = null;
    if (userMarker) { map.removeLayer(userMarker); userMarker = null; }
    if (userCircle) { map.removeLayer(userCircle); userCircle = null; }
    if (pinManual)  { map.removeLayer(pinManual);  pinManual  = null; }
    if (window.radioManual) { map.removeLayer(window.radioManual); window.radioManual = null; }

    document.getElementById('mbtn-quitar').style.display = 'none';
    document.getElementById('cerca-body').innerHTML =
        '<div class="cerca-placeholder">Usa "Mi ubicación" o "Fijar punto"<br>para ver las más cercanas</div>';
}

// ─────────────────────────────────────────────
//  CERCA DE TI
// ─────────────────────────────────────────────
function renderCercanas() {
    if (!userLoc || !datos.length) return;

    var lista = [];
    for (var i = 0; i < datos.length; i++) {
        var d = datos[i];
        var v = d[combustible];
        if (v !== null && !isNaN(v)) {
            lista.push({
                d:    d,
                precio: v,
                dist: distKm(userLoc.lat, userLoc.lng, d.Latitud, d.Longitud)
            });
        }
    }

    lista.sort(function(a,b){ return a.dist - b.dist; });

    var dentro = lista.filter(function(x){ return x.dist <= 2; });
    var top5 = dentro.length >= 2 ? dentro.slice(0,8) : lista.slice(0,5);
    var ps   = lista.map(function(x){ return x.precio; });

    var tituloCard = dentro.length >= 2
        ? '📍 ' + dentro.length + ' gasolineras en 2 km'
        : '📍 Más cercanas a ti';
    var cardHead = document.querySelector('#cerca-card .card-title');
    if (cardHead) cardHead.textContent = tituloCard;

    var html = '<div>';
    for (var j = 0; j < top5.length; j++) {
        var item = top5[j];
        var cat  = categorizar(item.precio, ps);
        var pCl  = cat === 'Barato' ? 'p-b' : (cat === 'Promedio' ? 'p-p' : 'p-c');
        var nom  = item.d.Nombre.length > 24 ? item.d.Nombre.slice(0,22) + '…' : item.d.Nombre;

        html +=
            '<div class="cerca-item" data-cj="' + j + '">' +
                '<div class="cerca-info">' +
                    '<div class="cerca-nombre">' + esc(nom) + '</div>' +
                    '<div class="cerca-dist">' + item.dist.toFixed(1) + ' km · ' + cat + '</div>' +
                '</div>' +
                '<div class="cerca-precio ' + pCl + '">$' + item.precio.toFixed(2) + '</div>' +
            '</div>';
    }
    html += '</div>';

    document.getElementById('cerca-body').innerHTML = html;

    var items = document.querySelectorAll('.cerca-item');
    for (var k = 0; k < items.length; k++) {
        (function(idx) {
            items[idx].addEventListener('click', function() {
                var item = top5[idx];
                mostrarDetalle(item.d, item.precio, ps);
                for (var m = 0; m < markersRef.length; m++) {
                    var ref = markersRef[m];
                    if (ref.numero === item.d.Numero) {
                        selMarker(m);
                        break;
                    }
                }
            });
        })(k);
    }
}

// ─────────────────────────────────────────────
//  COMBUSTIBLE
// ─────────────────────────────────────────────
function setCombustible(tipo) {
    combustible  = tipo;
    markerSelIdx = -1;
    syncPills();
    resetDetalle();
    render();
    if (userLoc) renderCercanas();
}

function syncPills() {
    var ts = ['Magna','Premium','Diesel'];
    for (var i = 0; i < ts.length; i++) {
        document.getElementById('pill-' + ts[i].toLowerCase())
            .classList.toggle('active', ts[i] === combustible);
    }
}

function detectarCombustibles() {
    var ts = ['Magna','Premium','Diesel'];
    for (var i = 0; i < ts.length; i++) {
        var t   = ts[i];
        var hay = false;
        for (var j = 0; j < datos.length; j++) {
            if (datos[j][t] !== null && !isNaN(datos[j][t])) { hay = true; break; }
        }
        document.getElementById('pill-' + t.toLowerCase()).disabled = !hay;
    }
}

// ─────────────────────────────────────────────
//  UTILS
// ─────────────────────────────────────────────
function categorizar(precio, todos) {
    var v = todos.filter(function(p){ return p !== null && !isNaN(p); });
    if (!v.length) return 'Promedio';
    var mn = Math.min.apply(null,v), mx = Math.max.apply(null,v);
    var r  = mx - mn;
    if (r === 0) return 'Promedio';
    if (precio <= mn + r/3)   return 'Barato';
    if (precio <= mn + 2*r/3) return 'Promedio';
    return 'Caro';
}

function getColor(cat) {
    if (cat === 'Barato')   return '#34c759';
    if (cat === 'Promedio') return '#ff9500';
    return '#ff3b30';
}

function distKm(la1, lo1, la2, lo2) {
    var R   = 6371;
    var dLa = (la2-la1) * Math.PI/180;
    var dLo = (lo2-lo1) * Math.PI/180;
    var a   = Math.sin(dLa/2)*Math.sin(dLa/2) +
              Math.cos(la1*Math.PI/180)*Math.cos(la2*Math.PI/180)*
              Math.sin(dLo/2)*Math.sin(dLo/2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function cap(s) {
    return (s||'').replace(/\b\w/g, function(c){ return c.toUpperCase(); });
}

function esc(s) {
    return (s||'')
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;');
}

function txt(id, v) {
    var el = document.getElementById(id);
    if (el) el.textContent = v;
}

function toggleCatFiltro(cat) {
    // Si ya está activo, lo desactiva
    catFiltro = (catFiltro === cat) ? null : cat;
    syncLeyenda();
    aplicarFiltroMapa();
}

function syncLeyenda() {
    var cats = ['Barato', 'Promedio', 'Caro'];
    cats.forEach(function(c) {
        var el = document.getElementById('ley-' + c.toLowerCase());
        if (!el) return;
        el.classList.remove('activo', 'opacado');
        if (catFiltro === null) return; // todas visibles, sin clase
        if (c === catFiltro) {
            el.classList.add('activo');
        } else {
            el.classList.add('opacado');
        }
    });
}

function aplicarFiltroMapa() {
    markersRef.forEach(function(ref) {
        var cat   = categorizar(ref.precio, markersRef.map(function(r){ return r.precio; }));
        var activo = (catFiltro === null || cat === catFiltro);

        // Opacidad via iconHTML
        var sz = 15, bw = 2;
        var color  = ref.color;
        var opacity = activo ? 1 : 0.18;

        ref.m.setIcon(L.divIcon({
            html: '<div style="width:' + sz + 'px;height:' + sz + 'px;' +
                  'background:' + color + ';border-radius:50%;' +
                  'border:' + bw + 'px solid white;' +
                  'box-shadow:0 1px 3px rgba(0,0,0,0.22);' +
                  'opacity:' + opacity + ';' +
                  'transition:all 0.2s"></div>',
            className: '', iconSize: [sz,sz], iconAnchor: [sz/2,sz/2]
        }));

        // Deshabilitar click en opacados
        if (activo) {
            ref.m.off('click');
            ref.m.on('click', (function(d, precio, ps, idx) {
                return function() {
                    selMarker(idx);
                    mostrarDetalle(d, precio, ps);
                };
            })(ref.d, ref.precio, markersRef.map(function(r){ return r.precio; }), ref._idx));
        } else {
            ref.m.off('click');
        }
    });
}