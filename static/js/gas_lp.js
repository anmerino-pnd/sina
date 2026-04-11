/* ============================================================
   Gas LP — Frontend Logic
   ============================================================ */

var datos        = [];
var tipoSel      = 'recipiente';
var capSel       = null;
var estadoSel    = '';
var munSel       = '';
var locSel       = '';
var entidadId    = null;
var municipioId  = null;
var localidadId  = null;
var idxSel       = -1;
var _locCache    = [];

// ─────────────────────────────────────────────
//  AUTOCOMPLETE ESTADO
// ─────────────────────────────────────────────
function filtrarEstados() {
    var q  = document.getElementById('inp-estado').value.toLowerCase().trim();
    var ks = Object.keys(CATALOGO).sort();
    var f;
    if (!q) {
        f = ks;
    } else {
        // Prioritize prefix matches, then include substring matches
        var prefix = ks.filter(function(k){ return k.toLowerCase().startsWith(q); });
        var contains = ks.filter(function(k){ 
            return !k.toLowerCase().startsWith(q) && k.toLowerCase().indexOf(q) !== -1; 
        });
        f = prefix.concat(contains);
    }
    renderDrop('drop-estado', f, false, seleccionarEstado);
}

function seleccionarEstado(val) {
    estadoSel = val;
    munSel    = '';
    locSel    = '';
    entidadId = null;
    municipioId = null;
    localidadId = null;
    _locCache = [];

    document.getElementById('inp-estado').value       = cap(val);
    document.getElementById('inp-municipio').value    = '';
    document.getElementById('inp-localidad').value    = '';
    document.getElementById('inp-municipio').disabled = false;
    document.getElementById('inp-localidad').disabled = true;
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
    var f;
    if (!q) {
        f = muns;
    } else {
        // Prioritize prefix matches, then include substring matches
        var prefix = muns.filter(function(m){ return m.toLowerCase().startsWith(q); });
        var contains = muns.filter(function(m){ 
            return !m.toLowerCase().startsWith(q) && m.toLowerCase().indexOf(q) !== -1; 
        });
        f = prefix.concat(contains);
    }
    renderDrop('drop-municipio', f, true, seleccionarMunicipio);
}

function seleccionarMunicipio(val) {
    munSel = val;
    locSel = '';
    municipioId = null;
    localidadId = null;
    _locCache = [];

    document.getElementById('inp-municipio').value    = cap(val);
    document.getElementById('inp-localidad').value    = '';
    document.getElementById('inp-localidad').disabled = false;
    document.getElementById('btn-ver').disabled       = true;
    cerrarDrop('municipio');
}

// ─────────────────────────────────────────────
//  AUTOCOMPLETE LOCALIDAD (desde API)
// ─────────────────────────────────────────────
async function filtrarLocalidades() {
    if (!estadoSel || !munSel) return;

    // Si ya tenemos cached, filtramos local
    if (_locCache.length > 0) {
        var q = document.getElementById('inp-localidad').value.toLowerCase().trim();
        var f;
        if (!q) {
            f = _locCache;
        } else {
            // Prioritize prefix matches, then include substring matches
            var prefix = _locCache.filter(function(l){ return l.nombre.toLowerCase().startsWith(q); });
            var contains = _locCache.filter(function(l){ 
                return !l.nombre.toLowerCase().startsWith(q) && l.nombre.toLowerCase().indexOf(q) !== -1; 
            });
            f = prefix.concat(contains);
        }
        renderLocalidadesDrop(f.map(function(l){ return l.nombre; }));
        return;
    }

    // Pedir localidades al backend (esto también nos da entidad_id y municipio_id)
    try {
        var url = '/api/v1/gas-lp/localidades?estado=' + encodeURIComponent(estadoSel) +
                  '&municipio=' + encodeURIComponent(munSel);
        var res  = await fetch(url);
        if (!res.ok) { renderLocalidadesDrop([]); return; }
        var json = await res.json();

        _locCache   = json.localidades || [];
        entidadId   = json.entidad_id;
        municipioId = json.municipio_id;
    } catch(e) {
        console.error('Error cargando localidades:', e);
        _locCache = [];
        renderLocalidadesDrop([]);
        return;
    }

    var q2 = document.getElementById('inp-localidad').value.toLowerCase().trim();
    var f2;
    if (!q2) {
        f2 = _locCache;
    } else {
        // Prioritize prefix matches, then include substring matches
        var prefix2 = _locCache.filter(function(l){ return l.nombre.toLowerCase().startsWith(q2); });
        var contains2 = _locCache.filter(function(l){ 
            return !l.nombre.toLowerCase().startsWith(q2) && l.nombre.toLowerCase().indexOf(q2) !== -1; 
        });
        f2 = prefix2.concat(contains2);
    }
    renderLocalidadesDrop(f2.map(function(l){ return l.nombre; }));
}

function renderLocalidadesDrop(nombres) {
    var drop = document.getElementById('drop-localidad');
    drop.innerHTML = '';

    if (nombres.length === 0) {
        drop.innerHTML = '<div class="drop-empty">Sin resultados</div>';
        drop.classList.add('open');
        return;
    }

    nombres.forEach(function(nombre) {
        var div  = document.createElement('div');
        div.className = 'drop-item';

        var span = document.createElement('span');
        span.textContent = cap(nombre);
        div.appendChild(span);

        div.addEventListener('mousedown', function(e){ e.preventDefault(); seleccionarLocalidad(nombre); });
        drop.appendChild(div);
    });

    drop.classList.add('open');
}

function seleccionarLocalidad(val) {
    locSel = val;

    var loc = _locCache.find(function(l){ return l.nombre === val; });
    if (loc) localidadId = loc.id;

    document.getElementById('inp-localidad').value = cap(val);
    document.getElementById('btn-ver').disabled    = false;
    cerrarDrop('localidad');
}

// ─────────────────────────────────────────────
//  DROPDOWN helpers
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
    if (t === 'localidad') filtrarLocalidades();
}

function cerrarDrop(t) {
    document.getElementById('drop-' + t).classList.remove('open');
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('#wrap-estado'))    cerrarDrop('estado');
    if (!e.target.closest('#wrap-municipio')) cerrarDrop('municipio');
    if (!e.target.closest('#wrap-localidad')) cerrarDrop('localidad');
});

// ─────────────────────────────────────────────
//  CARGAR LOCALIDAD
// ─────────────────────────────────────────────
async function cargarLocalidad() {
    if (!estadoSel || !munSel || !locSel) return;

    document.getElementById('sc-welcome').style.display = 'none';
    document.getElementById('sc-prox').style.display    = 'none';
    document.getElementById('dashboard').style.display  = 'none';

    // Asegurar IDs
    if (!entidadId || !municipioId || !localidadId) {
        var ids = await fetchLocationIds();
        if (!ids) { mostrarSinDatos(); return; }
        entidadId   = ids.entidad_id;
        municipioId = ids.municipio_id;
        localidadId = ids.localidad_id;
    }

    try {
        var url = '/api/v1/gas-lp/by-ids?entidad_id=' + entidadId +
                  '&municipio_id=' + encodeURIComponent(municipioId) +
                  '&localidad_id=' + localidadId;

        const res = await fetch(url);
        if (!res.ok) { mostrarSinDatos(); return; }

        const json = await res.json();

        // Combinar autotanques y recipientes con flag de tipo
        datos = [];
        if (json.autotanques) {
            json.autotanques.forEach(function(a){ datos.push({ ...a, tipo: 'autotanque' }); });
        }
        if (json.recipientes) {
            json.recipientes.forEach(function(r){ datos.push({ ...r, tipo: 'recipiente' }); });
        }

        if (datos.length === 0) { mostrarSinDatos(); return; }

        tipoSel  = 'recipiente';
        capSel   = null;
        idxSel   = -1;

        document.getElementById('dashboard').style.display = 'block';
        document.getElementById('nav-right').textContent   =
            cap(locSel) + ', ' + cap(munSel);

        syncPills();
        render();
        renderFooterFecha(json.fecha_datos);

    } catch (e) {
        console.error(e);
        alert('Error al cargar datos. Intenta de nuevo.');
    }
}

function mostrarSinDatos() {
    document.getElementById('prox-txt').innerHTML =
        'No hay datos para <strong>' + cap(locSel) + ', ' + cap(munSel) + ', ' + cap(estadoSel) + '</strong>.';
    document.getElementById('sc-prox').style.display = 'flex';
}

async function fetchLocationIds() {
    // Refrescar cache si está vacío
    if (_locCache.length === 0) {
        await filtrarLocalidades();
    }

    var loc = _locCache.find(function(l){ return l.nombre === locSel; });
    if (!loc) return null;

    return {
        entidad_id:   entidadId,
        municipio_id: municipioId,
        localidad_id: loc.id,
    };
}

// ─────────────────────────────────────────────
//  RENDER COMPLETO
// ─────────────────────────────────────────────
function render() {
    renderCapPills();   // Cap pills first — sets capSel to first available
    renderKPIs();
    renderRanking();
}

// ─────────────────────────────────────────────
//  KPIs
// ─────────────────────────────────────────────
function renderKPIs() {
    var filtrados = datosFiltrados();
    var ps = filtrados.map(function(d){ return d.precio; }).filter(function(v){ return v !== null && !isNaN(v); });

    txt('sec-label',   'Precios de Gas LP · ' + cap(locSel) + ', ' + cap(munSel));
    txt('rank-titulo', 'Proveedores · ' + labelTipo(tipoSel));

    if (ps.length === 0) {
        txt('kpi-prom','--'); txt('kpi-min','--'); txt('kpi-max','--'); txt('kpi-total','0');
        return;
    }

    var s = 0, mn = ps[0], mx = ps[0];
    for (var j = 0; j < ps.length; j++) {
        s += ps[j];
        if (ps[j] < mn) mn = ps[j];
        if (ps[j] > mx) mx = ps[j];
    }

    txt('kpi-prom',  '$' + (s/ps.length).toFixed(2));
    txt('kpi-min',   '$' + mn.toFixed(2));
    txt('kpi-max',   '$' + mx.toFixed(2));
    txt('kpi-total', '' + ps.length);
}

// ─────────────────────────────────────────────
//  CAP PILLS (solo para recipientes)
// ─────────────────────────────────────────────
function renderCapPills() {
    var row = document.getElementById('cap-row');
    if (tipoSel !== 'recipiente') {
        row.style.display = 'none';
        return;
    }

    row.style.display = 'flex';

    // Obtener capacidades únicas
    var caps = new Set();
    datos.filter(function(d){ return d.tipo === 'recipiente'; }).forEach(function(d){
        if (d.capacidad_recipiente != null) caps.add(d.capacidad_recipiente);
    });

    var capsArr = Array.from(caps).sort(function(a,b){ return a - b; });

    if (capsArr.length === 0) {
        row.style.display = 'none';
        return;
    }

    // Default: if no capacity selected, pick first available BEFORE building HTML
    if (capSel === null) {
        capSel = capsArr[0];
    }

    // Build pills with active class already set
    var html = '<span class="pills-label">Capacidad</span>';
    capsArr.forEach(function(c){
        html += '<button class="pill cap-pill ' + (capSel == c ? 'active' : '') + '" onclick="setCapacidad(' + c + ')">' + c + ' kg</button>';
    });
    row.innerHTML = html;
}

// ─────────────────────────────────────────────
//  FILTROS
// ─────────────────────────────────────────────
function datosFiltrados() {
    var lista = datos.filter(function(d){ return d.tipo === tipoSel; });

    if (tipoSel === 'recipiente' && capSel !== null) {
        var capNum = parseInt(capSel);
        lista = lista.filter(function(d){ return d.capacidad_recipiente === capNum; });
    }

    return lista;
}

// ─────────────────────────────────────────────
//  RANKING
// ─────────────────────────────────────────────
function renderRanking() {
    var lista = datosFiltrados();
    lista.sort(function(a,b){ return a.precio - b.precio; });

    var ps    = lista.map(function(x){ return x.precio; });
    var top10 = lista.slice(0,10);
    var tbody = document.getElementById('rank-body');

    if (top10.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#ccc;padding:18px">Sin datos para este filtro</td></tr>';
        return;
    }

    var html = '';
    for (var j = 0; j < top10.length; j++) {
        var item = top10[j];
        var cat  = categorizar(item.precio, ps);
        var bCl  = cat === 'Barato' ? 'b-b' : (cat === 'Promedio' ? 'b-p' : 'b-c');
        var pCl  = cat === 'Barato' ? 'p-b' : (cat === 'Promedio' ? 'p-p' : 'p-c');
        var nom  = item.marca_comercial || item.numero_permiso || '—';
        if (nom.length > 28) nom = nom.slice(0,26) + '…';

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

                var all = tbody.querySelectorAll('tr');
                for (var r = 0; r < all.length; r++) all[r].classList.remove('sel');
                rows[idx].classList.add('sel');

                mostrarDetalle(item, ps);
            });
        })(k);
    }
}

// ─────────────────────────────────────────────
//  DETALLE
// ─────────────────────────────────────────────
function mostrarDetalle(item, todosPrecios) {
    var cat = categorizar(item.precio, todosPrecios);

    document.getElementById('detail-ph').style.display      = 'none';
    document.getElementById('detail-content').style.display = 'block';
    document.getElementById('detail-card').classList.add('filled');

    txt('d-marca',   item.marca_comercial || 'Sin marca comercial');
    txt('d-permiso', item.numero_permiso || '—');

    var tipoLabel = item.tipo === 'autotanque' ? 'Autotanque' : 'Recipiente';
    var extra = '';
    if (item.capacidad_recipiente != null) {
        extra = ' · ' + item.capacidad_recipiente + ' kg';
    }
    txt('d-meta', tipoLabel + extra + ' · ' + cat);
    txt('d-precio', '$' + item.precio.toFixed(2));

    // Tags
    var tagsHtml = '<span class="tag tipo-' + item.tipo + '">' + tipoLabel + '</span>';
    if (item.capacidad_recipiente != null) {
        tagsHtml += '<span class="tag capacidad">' + item.capacidad_recipiente + ' kg</span>';
    }
    tagsHtml += '<span class="tag">Última actualización: ' + formatFecha(item.fecha_extraccion) + '</span>';
    document.getElementById('d-tags').innerHTML = tagsHtml;
}

function resetDetalle() {
    document.getElementById('detail-ph').style.display      = 'flex';
    document.getElementById('detail-content').style.display = 'none';
    document.getElementById('detail-card').classList.remove('filled');
}

// ─────────────────────────────────────────────
//  FOOTER FECHA
// ─────────────────────────────────────────────
function renderFooterFecha(fecha) {
    txt('footer-fecha', formatFecha(fecha));
}

function formatFecha(fecha) {
    if (!fecha) return '—';
    try {
        var d = new Date(fecha);
        if (isNaN(d.getTime())) return '—';
        var opciones = { day: 'numeric', month: 'short', year: 'numeric' };
        return d.toLocaleDateString('es-MX', opciones);
    } catch(e) {
        return '—';
    }
}

// ─────────────────────────────────────────────
//  TIPO / CAPACIDAD
// ─────────────────────────────────────────────
function setTipo(tipo) {
    tipoSel = tipo;
    capSel  = null;
    idxSel  = -1;
    resetDetalle();
    syncPills();
    render();
}

function setCapacidad(cap) {
    capSel = cap;
    idxSel = -1;
    resetDetalle();
    renderCapPills();
    renderKPIs();
    renderRanking();
}

function syncPills() {
    document.getElementById('pill-autotanque')
        .classList.toggle('active', tipoSel === 'autotanque');
    document.getElementById('pill-recipiente')
        .classList.toggle('active', tipoSel === 'recipiente');
}

function labelTipo(t) {
    return t === 'autotanque' ? 'Autotanques' : 'Recipientes';
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

function cap(s) {
    return (s||'').replace(/\b\w/g, function(c){ return c.toUpperCase(); });
}

function esc(s) {
    return (s||'')
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;')
        .replace(/'/g,'&#39;');
}

function txt(id, v) {
    var el = document.getElementById(id);
    if (el) el.textContent = v;
}

function formatFecha(fecha) {
    if (!fecha) return '—';
    try {
        var d = new Date(fecha);
        var opciones = { day: 'numeric', month: 'short', year: 'numeric' };
        return d.toLocaleDateString('es-MX', opciones);
    } catch(e) {
        return '—';
    }
}
