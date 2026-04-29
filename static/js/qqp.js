// ═══════════════════════════════════════════════════════
//  QQP — Canasta Básica Dashboard (FIXED)
// ═══════════════════════════════════════════════════════

var CATALOGO   = {};
var DATA       = null;
var estadoSel  = '';
var munSel     = '';
var selecciones = {};
var itemActivo  = null;

// ── Paleta ─────────────────────────────────────────────
var C = {
    primario:    '#3D264E',
    primarioClr: '#5E4172',
    dorado:      '#C5B075',
    cafe:        '#493B31',
    crema:       '#E2D2C3',
    negro:       '#15110C',
    sec:         '#6B5E53',
    ter:         '#A89B8F',
    fondo:       '#F7F3EF',
    blanco:      '#FFFFFF',
    border:      '#DDD5CC',
};

function degradadoPurpura(n) {
    var base = [
        '#1E0F2E','#2A1740','#3D264E','#5E4172',
        '#7E5E96','#9E7EBA','#BEA0D4','#D8C4E6','#EEDCF5'
    ];
    if (n <= 0) return [];
    if (n === 1) return [base[2]];
    var r = [];
    for (var i = 0; i < n; i++) {
        var idx = Math.round(i * (base.length - 1) / (n - 1));
        r.push(base[idx]);
    }
    return r;
}

var LAYOUT_BASE = {
    font: { family: 'Inter, -apple-system, sans-serif', color: C.negro, size: 13 },
    paper_bgcolor: C.blanco,
    plot_bgcolor:  C.blanco,
    margin: { l: 10, r: 10, t: 10, b: 10 },
    hoverlabel: {
        bgcolor: 'white',
        font: { size: 12, family: 'Inter, sans-serif', color: C.negro },
        bordercolor: C.border,
    },
    showlegend: false,
};

var PLOTLY_CFG = { displayModeBar: false, responsive: true };

// ═══════════════════════════════════════════════════════
//  CATÁLOGO
// ═══════════════════════════════════════════════════════
(function() {
    fetch('/api/v1/qqp/catalogo')
        .then(function(r) { return r.json(); })
        .then(function(d) { CATALOGO = d; })
        .catch(function(e) { console.error('Error catálogo QQP:', e); });
})();

// ═══════════════════════════════════════════════════════
//  AUTOCOMPLETE
// ═══════════════════════════════════════════════════════
function filtrarEstados() {
    var q = el('inp-estado').value.toLowerCase().trim();
    var ks = Object.keys(CATALOGO).sort();
    var f = !q ? ks : ks.filter(function(k){ return k.toLowerCase().startsWith(q); })
        .concat(ks.filter(function(k){ return !k.toLowerCase().startsWith(q) && k.toLowerCase().indexOf(q)!==-1; }));
    renderDrop('drop-estado', f, seleccionarEstado);
}

function seleccionarEstado(val) {
    estadoSel = val; munSel = '';
    el('inp-estado').value = cap(val);
    el('inp-municipio').value = '';
    el('inp-municipio').disabled = false;
    el('btn-ver').disabled = true;
    cerrarDrop('estado');
}

function filtrarMunicipios() {
    if (!estadoSel) return;
    var q = el('inp-municipio').value.toLowerCase().trim();
    var muns = CATALOGO[estadoSel] || [];
    var f = !q ? muns : muns.filter(function(m){ return m.toLowerCase().startsWith(q); })
        .concat(muns.filter(function(m){ return !m.toLowerCase().startsWith(q) && m.toLowerCase().indexOf(q)!==-1; }));
    renderDrop('drop-municipio', f, seleccionarMunicipio);
}

function seleccionarMunicipio(val) {
    munSel = val;
    el('inp-municipio').value = cap(val);
    el('btn-ver').disabled = false;
    cerrarDrop('municipio');
}

function renderDrop(id, items, cb) {
    var drop = el(id);
    drop.innerHTML = '';
    if (!items.length) {
        drop.innerHTML = '<div class="drop-empty">Sin resultados</div>';
        drop.classList.add('open'); return;
    }
    items.forEach(function(item) {
        var d = document.createElement('div');
        d.className = 'drop-item';
        d.textContent = cap(item);
        d.addEventListener('mousedown', function(e){ e.preventDefault(); cb(item); });
        drop.appendChild(d);
    });
    drop.classList.add('open');
}

function abrirDrop(t) { t==='estado' ? filtrarEstados() : filtrarMunicipios(); }
function cerrarDrop(t) { el('drop-'+t).classList.remove('open'); }

document.addEventListener('click', function(e) {
    if (!e.target.closest('#wrap-estado'))    cerrarDrop('estado');
    if (!e.target.closest('#wrap-municipio')) cerrarDrop('municipio');
});

// ═══════════════════════════════════════════════════════
//  CARGAR CANASTA
// ═══════════════════════════════════════════════════════
async function cargarCanasta() {
    if (!estadoSel || !munSel) return;
    el('sc-welcome').style.display = 'none';
    el('sc-empty').style.display   = 'none';
    el('dashboard').style.display  = 'none';

    try {
        var res = await fetch(
            '/api/v1/qqp/canasta?estado=' + encodeURIComponent(estadoSel) +
            '&municipio=' + encodeURIComponent(munSel)
        );
        var json = await res.json();

        if (json.error || !json.items || Object.keys(json.items).length === 0) {
            el('empty-txt').innerHTML = 'No encontramos datos para <strong>' + cap(munSel) + ', ' + cap(estadoSel) + '</strong>.';
            el('sc-empty').style.display = 'flex';
            return;
        }

        DATA = json;
        selecciones = {};
        itemActivo = null;
        var items = Object.keys(DATA.items);
        items.forEach(function(item) { selecciones[item] = DATA.items[item].default_presentacion; });
        if (items.length) itemActivo = items[0];

        el('dashboard').style.display = 'block';
        el('nav-right').textContent = cap(munSel) + ', ' + cap(estadoSel) + ' · Profeco QQP';
        renderTodo();

    } catch (e) {
        console.error(e);
        el('empty-txt').textContent = 'Error al cargar datos. Intenta de nuevo.';
        el('sc-empty').style.display = 'flex';
    }
}

// ═══════════════════════════════════════════════════════
//  RENDER PRINCIPAL
// ═══════════════════════════════════════════════════════
function renderTodo() {
    renderKPIs();
    renderSidebar();
    renderResumen();
    renderRanking();
    renderDumbbell();
    renderDetalle();
    renderComparativo();
    renderInsights();
}

// ═══════════════════════════════════════════════════════
//  KPIs
// ═══════════════════════════════════════════════════════
function renderKPIs() {
    var r = DATA.resumen;
    var total = calcTotal();
    txt('sec-label', cap(munSel) + ', ' + cap(estadoSel) + ' · ' + r.n_items + ' categorías de canasta básica');
    txt('kpi-canasta', '$' + total.toFixed(0));
    txt('kpi-cadenas', '' + r.n_cadenas);
    txt('kpi-productos', r.n_items + ' categorías · ' + r.n_productos_total + ' productos');
}

function calcTotal() {
    var t = 0;
    Object.keys(selecciones).forEach(function(item) {
        var op = mejorOp(item, selecciones[item]);
        if (op) t += op.precio;
    });
    return t;
}

function mejorOp(item, pres) {
    if (!DATA || !DATA.items[item]) return null;
    var p = DATA.items[item].presentaciones[pres];
    if (!p || !p.opciones || !p.opciones.length) return null;
    return p.opciones[0];
}

// ═══════════════════════════════════════════════════════
//  INSIGHTS — Información útil calculada
// ═══════════════════════════════════════════════════════
function calcInsights() {
    var items = Object.keys(selecciones);
    var nTotal = items.length;
    var totalMulti = calcTotal();

    // --- Cadenas usadas en la canasta óptima ---
    var tiendasUsadas = {};
    items.forEach(function(item) {
        var op = mejorOp(item, selecciones[item]);
        if (op) tiendasUsadas[op.cadena] = (tiendasUsadas[op.cadena] || 0) + 1;
    });
    var nTiendas = Object.keys(tiendasUsadas).length;

    // --- Mejor cadena individual (cobertura >= 80%) ---
    var cadenas = {};
    items.forEach(function(item) {
        var pres = selecciones[item];
        var iData = DATA.items[item];
        if (!iData || !iData.presentaciones[pres]) return;
        var visto = {};
        iData.presentaciones[pres].opciones.forEach(function(op) {
            if (!visto[op.cadena] || op.precio < visto[op.cadena]) visto[op.cadena] = op.precio;
        });
        Object.keys(visto).forEach(function(c) {
            if (!cadenas[c]) cadenas[c] = { total: 0, n: 0 };
            cadenas[c].total += visto[c];
            cadenas[c].n += 1;
        });
    });

    var umbralAlto = Math.max(1, Math.floor(nTotal * 0.8));
    var mejorCadena = null;
    var mejorTotal = Infinity;
    Object.keys(cadenas).forEach(function(c) {
        if (cadenas[c].n >= umbralAlto) {
            if (cadenas[c].total < mejorTotal) {
                mejorTotal = cadenas[c].total;
                mejorCadena = c;
            }
        }
    });

    // --- Producto con mayor variación de precio ---
    var maxVar = { item: null, diff: 0, min: 0, max: 0 };
    items.forEach(function(item) {
        var pres = selecciones[item];
        var iData = DATA.items[item];
        if (!iData || !iData.presentaciones[pres]) return;
        var ops = iData.presentaciones[pres].opciones;
        if (ops.length < 2) return;
        var diff = ops[ops.length - 1].precio - ops[0].precio;
        if (diff > maxVar.diff) {
            maxVar = { item: item, diff: diff, min: ops[0].precio, max: ops[ops.length - 1].precio };
        }
    });

    return {
        totalMulti: totalMulti,
        nTiendas: nTiendas,
        tiendasUsadas: tiendasUsadas,
        mejorCadena: mejorCadena,
        mejorCadenaTotal: mejorTotal,
        mejorCadenaN: mejorCadena ? cadenas[mejorCadena].n : 0,
        ahorro: mejorCadena ? (mejorTotal - totalMulti) : 0,
        maxVar: maxVar,
    };
}

function renderInsights() {
    var ctr = el('insights-row');
    if (!ctr) return;
    ctr.innerHTML = '';

    var info = calcInsights();

    // Card 1: Ahorro comprando en varias tiendas
    if (info.mejorCadena && info.ahorro > 0) {
        var card1 = document.createElement('div');
        card1.className = 'insight-card';
        var pct = ((info.ahorro / info.mejorCadenaTotal) * 100).toFixed(0);
        card1.innerHTML =
            '<span class="insight-ico">💰</span>' +
            '<div class="insight-body">' +
                '<div class="insight-title">Ahorras $' + info.ahorro.toFixed(0) + ' (' + pct + '%) comprando en ' + info.nTiendas + ' tiendas</div>' +
                '<div class="insight-desc">Tu canasta óptima cuesta <strong>$' + info.totalMulti.toFixed(0) + '</strong> en ' + info.nTiendas +
                ' tiendas distintas. Si prefieres ir a una sola, <strong>' + esc(info.mejorCadena) + '</strong> te sale en $' + info.mejorCadenaTotal.toFixed(0) +
                ' (' + info.mejorCadenaN + '/' + Object.keys(selecciones).length + ' productos).</div>' +
            '</div>';
        ctr.appendChild(card1);
    }

    // Card 2: Mayor variación de precio
    if (info.maxVar.item) {
        var card2 = document.createElement('div');
        card2.className = 'insight-card';
        card2.innerHTML =
            '<span class="insight-ico">📊</span>' +
            '<div class="insight-body">' +
                '<div class="insight-title">' + esc(info.maxVar.item) + ' tiene la mayor variación de precio</div>' +
                '<div class="insight-desc">Va de <strong>$' + info.maxVar.min.toFixed(0) + '</strong> a <strong>$' + info.maxVar.max.toFixed(0) +
                '</strong> — una diferencia de $' + info.maxVar.diff.toFixed(0) + '. Aquí es donde más conviene comparar.</div>' +
            '</div>';
        ctr.appendChild(card2);
    }

    // Card 3: Resumen de tiendas necesarias
    if (info.nTiendas > 0) {
        var tiendaLines = Object.keys(info.tiendasUsadas)
            .sort(function(a, b) { return info.tiendasUsadas[b] - info.tiendasUsadas[a]; })
            .map(function(c) { return esc(c) + ' (' + info.tiendasUsadas[c] + ')'; })
            .join(', ');
        var card3 = document.createElement('div');
        card3.className = 'insight-card';
        card3.innerHTML =
            '<span class="insight-ico">🏪</span>' +
            '<div class="insight-body">' +
                '<div class="insight-title">Tu canasta óptima requiere ' + info.nTiendas + ' tienda' + (info.nTiendas > 1 ? 's' : '') + '</div>' +
                '<div class="insight-desc">' + tiendaLines + '</div>' +
            '</div>';
        ctr.appendChild(card3);
    }
}

// ═══════════════════════════════════════════════════════
//  SIDEBAR IZQUIERDA
//  FIX: Use DOM methods instead of innerHTML += to
//       preserve radio checked state and event listeners
// ═══════════════════════════════════════════════════════
function renderSidebar() {
    var list = el('sidebar-list');
    list.innerHTML = '';
    var items = Object.keys(DATA.items);
    txt('sidebar-count', items.length + ' categorías');

    items.forEach(function(item) {
        var iData = DATA.items[item];
        var presSel = selecciones[item];
        var esActivo = item === itemActivo;
        var nPres = Object.keys(iData.presentaciones).length;

        var div = document.createElement('div');
        div.className = 'sb-item' + (esActivo ? ' activo' : '');

        // ── Cabecera ──
        var head = document.createElement('div');
        head.className = 'sb-item-head';
        head.addEventListener('click', function() { toggleItem(item); });

        var infoDiv = document.createElement('div');
        infoDiv.className = 'sb-item-info';

        var nombreDiv = document.createElement('div');
        nombreDiv.className = 'sb-item-nombre';
        nombreDiv.textContent = item;

        var presDiv = document.createElement('div');
        presDiv.className = 'sb-item-pres';
        presDiv.textContent = presSel;

        infoDiv.appendChild(nombreDiv);
        infoDiv.appendChild(presDiv);

        var countSpan = document.createElement('span');
        countSpan.className = 'sb-item-count';
        countSpan.textContent = nPres + ' presentaciones';

        head.appendChild(infoDiv);
        head.appendChild(countSpan);
        div.appendChild(head);

        // ── Opciones de presentación ──
        var opcDiv = document.createElement('div');
        opcDiv.className = 'sb-opciones';

        var presKeys = Object.keys(iData.presentaciones);
        presKeys.sort(function(a, b) {
            return iData.presentaciones[a].opciones[0].precio - iData.presentaciones[b].opciones[0].precio;
        });

        presKeys.forEach(function(pres) {
            var ops = iData.presentaciones[pres].opciones;
            var nCad = contarCadenas(ops);
            var esSel = pres === presSel;
            var precioMin = ops[0].precio;

            // ── FIX: Build label entirely with DOM methods ──
            var label = document.createElement('label');
            label.className = 'sb-opcion' + (esSel ? ' seleccionada' : '');

            var radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'pres-' + item.replace(/\s/g, '_');
            radio.checked = esSel;
            radio.addEventListener('change', function() {
                cambiarPresentacion(item, pres);
            });

            var nombreSpan = document.createElement('span');
            nombreSpan.className = 'sb-opcion-nombre';
            nombreSpan.textContent = pres;

            var precioSpan = document.createElement('span');
            precioSpan.className = 'sb-opcion-precio';
            precioSpan.textContent = '$' + precioMin.toFixed(0);

            var countSpanOp = document.createElement('span');
            countSpanOp.className = 'sb-opcion-count';
            countSpanOp.textContent = nCad + ' cadenas';

            label.appendChild(radio);
            label.appendChild(nombreSpan);
            label.appendChild(precioSpan);
            label.appendChild(countSpanOp);
            opcDiv.appendChild(label);
        });

        div.appendChild(opcDiv);
        list.appendChild(div);
    });
}

function toggleItem(item) {
    if (itemActivo === item) return;
    itemActivo = item;
    renderSidebar();
    renderDetalle();
    renderComparativo();
}

function cambiarPresentacion(item, pres) {
    selecciones[item] = pres;
    renderTodo();
}

// ═══════════════════════════════════════════════════════
//  RESUMEN DERECHA
// ═══════════════════════════════════════════════════════
function renderResumen() {
    var list = el('resumen-list');
    list.innerHTML = '';
    var items = Object.keys(DATA.items);
    var total = 0;

    items.forEach(function(item) {
        var pres = selecciones[item];
        var op = mejorOp(item, pres);
        var precio = op ? op.precio : 0;
        total += precio;

        var div = document.createElement('div');
        div.className = 'rs-item' + (item === itemActivo ? ' activo' : '');
        div.addEventListener('click', function() { toggleItem(item); });

        // Build with DOM to keep event listeners clean
        var infoDiv = document.createElement('div');
        infoDiv.className = 'rs-item-info';

        var nameDiv = document.createElement('div');
        nameDiv.className = 'rs-item-nombre';
        nameDiv.textContent = item;

        var detDiv = document.createElement('div');
        detDiv.className = 'rs-item-detalle';
        detDiv.textContent = trun(pres, 28) + (op ? ' · ' + op.cadena : '');

        infoDiv.appendChild(nameDiv);
        infoDiv.appendChild(detDiv);

        var priceDiv = document.createElement('div');
        priceDiv.className = 'rs-item-precio';
        priceDiv.textContent = op ? '$' + precio.toFixed(2) : 'N/D';

        div.appendChild(infoDiv);
        div.appendChild(priceDiv);
        list.appendChild(div);
    });

    txt('resumen-total', '$' + total.toFixed(0));
    txt('resumen-footer', items.length + ' categorías · Precio más bajo por presentación seleccionada');
}

// ═══════════════════════════════════════════════════════
//  GRÁFICA: Ranking de cadenas
//  FIX: Added coverage info, removed x-axis, more space
// ═══════════════════════════════════════════════════════
function renderRanking() {
    var cadenas = {};
    var nTotal = Object.keys(selecciones).length;

    Object.keys(selecciones).forEach(function(item) {
        var pres = selecciones[item];
        var iData = DATA.items[item];
        if (!iData || !iData.presentaciones[pres]) return;
        var visto = {};
        iData.presentaciones[pres].opciones.forEach(function(op) {
            if (!visto[op.cadena] || op.precio < visto[op.cadena]) visto[op.cadena] = op.precio;
        });
        Object.keys(visto).forEach(function(c) {
            if (!cadenas[c]) cadenas[c] = { total: 0, n: 0 };
            cadenas[c].total += visto[c];
            cadenas[c].n += 1;
        });
    });

    var umbral = Math.max(1, Math.floor(nTotal * 0.4));

    var lista = Object.keys(cadenas)
        .filter(function(c) { return cadenas[c].n >= umbral; })
        .map(function(c) { return { cadena: c, total: cadenas[c].total, n: cadenas[c].n }; })
        .sort(function(a, b) { return a.total - b.total; });

    if (!lista.length) {
        el('chart-ranking').innerHTML = '<div style="padding:30px;text-align:center;color:'+C.ter+'">Sin datos suficientes</div>';
        return;
    }

    var n = lista.length;
    var cols = degradadoPurpura(n).reverse();

    var trace = {
        type: 'bar', orientation: 'h',
        x: lista.map(function(d){ return d.total; }),
        y: lista.map(function(d){ return d.cadena; }),
        marker: { color: cols, line: { width: 0 } },
        hovertemplate: '<b>%{y}</b><br>Canasta: $%{x:,.0f}<br>(%{customdata})<extra></extra>',
        customdata: lista.map(function(d){ return d.n + '/' + nTotal + ' categorías'; }),
    };

    // FIX: Annotations with coverage info and more offset
    var annots = lista.map(function(d, i) {
        return {
            x: d.total, y: d.cadena,
            text: '$' + d.total.toFixed(0) + '  (' + d.n + '/' + nTotal + ')',
            showarrow: false, xanchor: 'left', xshift: 12,
            font: { size: i === 0 ? 13 : 11, color: i === 0 ? C.negro : C.sec, weight: i === 0 ? 700 : 400 },
        };
    });

    var layout = mL({
        height: Math.max(220, n * 56 + 60),
        margin: { l: 140, r: 90, t: 10, b: 10 },
        // FIX: No x-axis (annotations already show prices)
        xaxis: { showgrid: false, showticklabels: false, zeroline: false, visible: false },
        yaxis: { autorange: 'reversed', tickfont: { size: 12, color: C.negro }, automargin: true },
        annotations: annots,
        bargap: 0.35,
    });

    Plotly.newPlot('chart-ranking', [trace], layout, PLOTLY_CFG);
}

// ═══════════════════════════════════════════════════════
//  GRÁFICA: Dumbbell
//  FIX: Removed x-axis, increased spacing
// ═══════════════════════════════════════════════════════
function renderDumbbell() {
    var items = Object.keys(selecciones);
    var datos = [];

    items.forEach(function(item) {
        var pres = selecciones[item];
        var iData = DATA.items[item];
        if (!iData || !iData.presentaciones[pres]) return;
        var ops = iData.presentaciones[pres].opciones;
        if (!ops.length) return;
        datos.push({
            item: item,
            min: ops[0].precio,
            max: ops[ops.length - 1].precio,
            cadMin: ops[0].cadena,
            cadMax: ops[ops.length - 1].cadena,
        });
    });

    datos.sort(function(a, b) { return b.min - a.min; });

    var traces = [];
    datos.forEach(function(d) {
        // Line connecting min-max
        traces.push({
            type: 'scatter', x: [d.min, d.max], y: [d.item, d.item],
            mode: 'lines', line: { color: C.border, width: 2 },
            showlegend: false, hoverinfo: 'skip',
        });
        // Min dot
        traces.push({
            type: 'scatter', x: [d.min], y: [d.item],
            mode: 'markers', marker: { color: C.primario, size: 10 },
            showlegend: false,
            hovertemplate: '<b>' + esc(d.item) + '</b><br>Más barato: $' + d.min.toFixed(2) + '<br>' + esc(d.cadMin) + '<extra></extra>',
        });
        // Max dot
        traces.push({
            type: 'scatter', x: [d.max], y: [d.item],
            mode: 'markers', marker: { color: C.dorado, size: 10 },
            showlegend: false,
            hovertemplate: '<b>' + esc(d.item) + '</b><br>Más caro: $' + d.max.toFixed(2) + '<br>' + esc(d.cadMax) + '<extra></extra>',
        });
    });

    // FIX: Annotations with more xshift for breathing room
    var annots = [];
    datos.forEach(function(d) {
        annots.push({
            x: d.min, y: d.item,
            text: '$' + d.min.toFixed(0),
            showarrow: false, xanchor: 'right', xshift: -14,
            font: { size: 11, color: C.primario },
        });
        annots.push({
            x: d.max, y: d.item,
            text: '$' + d.max.toFixed(0),
            showarrow: false, xanchor: 'left', xshift: 14,
            font: { size: 11, color: C.dorado },
        });
    });

    // Legend annotation
    annots.push({
        xref: 'paper', yref: 'paper', x: 0, y: 1.06,
        text: '<span style="color:'+C.primario+'">●</span> Más barato  <span style="color:'+C.dorado+'">●</span> Más caro',
        showarrow: false, font: { size: 11 },
    });

    var layout = mL({
        // FIX: More height per item (48px vs 40px)
        height: Math.max(350, datos.length * 48 + 70),
        margin: { l: 150, r: 80, t: 35, b: 10 },
        // FIX: No x-axis at all
        xaxis: { showgrid: false, showticklabels: false, zeroline: false, visible: false },
        yaxis: { showgrid: false, tickfont: { size: 12, color: C.negro } },
        annotations: annots,
    });

    Plotly.newPlot('chart-dumbbell', traces, layout, PLOTLY_CFG);
}

// ═══════════════════════════════════════════════════════
//  GRÁFICA: Detalle item
//  FIX: Removed x-axis, more spacing
// ═══════════════════════════════════════════════════════
function renderDetalle() {
    var card = el('card-detalle');
    if (!itemActivo || !DATA.items[itemActivo]) { card.style.display = 'none'; return; }
    card.style.display = 'block';

    var iData = DATA.items[itemActivo];
    var presKeys = Object.keys(iData.presentaciones);
    var datos = presKeys.map(function(p) {
        var ops = iData.presentaciones[p].opciones;
        return { pres: p, precio: ops[0].precio, cadena: ops[0].cadena, nCad: contarCadenas(ops), esSel: p === selecciones[itemActivo] };
    });
    datos.sort(function(a, b) { return a.precio - b.precio; });

    var cols = datos.map(function(d) { return d.esSel ? C.primario : C.crema; });
    var n = datos.length;

    var trace = {
        type: 'bar', orientation: 'h',
        x: datos.map(function(d){ return d.precio; }),
        y: datos.map(function(d){ return d.pres; }),
        marker: { color: cols, line: { width: 0 } },
        hovertemplate: '<b>%{y}</b><br>Desde $%{x:,.2f}<extra></extra>',
    };

    // FIX: xshift instead of text padding, more offset
    var annots = datos.map(function(d) {
        return {
            x: d.precio, y: d.pres,
            text: '$' + d.precio.toFixed(0) + ' · ' + d.cadena + ' (' + d.nCad + ')',
            showarrow: false, xanchor: 'left', xshift: 12,
            font: { size: 10, color: d.esSel ? C.primario : C.sec },
        };
    });

    var layout = mL({
        // FIX: More height per bar (44px vs 38px)
        height: Math.max(200, n * 44 + 60),
        margin: { l: 230, r: 160, t: 10, b: 10 },
        // FIX: No x-axis
        xaxis: { showgrid: false, showticklabels: false, zeroline: false, visible: false },
        yaxis: { autorange: 'reversed', showgrid: false, tickfont: { size: 10, color: C.negro }, automargin: true },
        annotations: annots,
        bargap: 0.3,
    });

    Plotly.newPlot('chart-detalle-plot', [trace], layout, PLOTLY_CFG);
    txt('chart-detalle-title', itemActivo);
    txt('chart-detalle-sub', cap(munSel) + ' · Precio más bajo por presentación');
}

// ═══════════════════════════════════════════════════════
//  GRÁFICA: Comparativo por cadena
//  FIX: Removed x-axis, more spacing
// ═══════════════════════════════════════════════════════
function renderComparativo() {
    var card = el('card-comparativo');
    if (!itemActivo || !DATA.items[itemActivo]) { card.style.display = 'none'; return; }

    var presSel = selecciones[itemActivo];
    var iData = DATA.items[itemActivo];
    if (!iData.presentaciones[presSel]) { card.style.display = 'none'; return; }
    card.style.display = 'block';

    var ops = iData.presentaciones[presSel].opciones;
    var porCad = {};
    ops.forEach(function(op) {
        if (!porCad[op.cadena] || op.precio < porCad[op.cadena].precio) porCad[op.cadena] = op;
    });

    var datos = Object.keys(porCad)
        .map(function(c) { return { cadena: c, precio: porCad[c].precio, marca: porCad[c].marca }; })
        .sort(function(a, b) { return a.precio - b.precio; });

    if (!datos.length) { card.style.display = 'none'; return; }

    var n = datos.length;
    var pMin = datos[0].precio;
    var cols = datos.map(function(d, i) { return i === 0 ? C.primario : C.crema; });

    var trace = {
        type: 'bar', orientation: 'h',
        x: datos.map(function(d){ return d.precio; }),
        y: datos.map(function(d){ return d.cadena; }),
        marker: { color: cols, line: { width: 0 } },
        hovertemplate: '<b>%{y}</b><br>$%{x:,.2f}<extra></extra>',
    };

    // FIX: xshift instead of text padding
    var annots = datos.map(function(d, i) {
        var diff = d.precio - pMin;
        var t = '$' + d.precio.toFixed(2);
        if (diff > 0) t += '  (+$' + diff.toFixed(2) + ')';
        return {
            x: d.precio, y: d.cadena, text: t,
            showarrow: false, xanchor: 'left', xshift: 12,
            font: { size: 11, color: i === 0 ? C.primario : C.sec },
        };
    });

    var layout = mL({
        // FIX: More height per bar (50px vs 44px)
        height: Math.max(200, n * 50 + 60),
        margin: { l: 180, r: 130, t: 10, b: 10 },
        // FIX: No x-axis
        xaxis: { showgrid: false, showticklabels: false, zeroline: false, visible: false },
        yaxis: { autorange: 'reversed', showgrid: false, tickfont: { size: 12, color: C.negro }, automargin: true },
        annotations: annots,
        bargap: 0.35,
    });

    Plotly.newPlot('chart-comparativo', [trace], layout, PLOTLY_CFG);
    txt('chart-comp-title', itemActivo + ' · ' + trun(presSel, 40));
    txt('chart-comp-sub', 'Comparativo por cadena');
}

// ═══════════════════════════════════════════════════════
//  UTILS
// ═══════════════════════════════════════════════════════
function el(id)   { return document.getElementById(id); }
function cap(s)   { return (s||'').replace(/\b\w/g, function(c){ return c.toUpperCase(); }); }
function esc(s)   { return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function txt(id,v){ var e=el(id); if(e) e.textContent=v; }
function trun(s,n){ return !s ? '' : s.length>n ? s.slice(0,n-1)+'…' : s; }

function contarCadenas(ops) {
    var s = {};
    ops.forEach(function(o){ s[o.cadena]=1; });
    return Object.keys(s).length;
}

function mL(custom) {
    var r = {};
    Object.keys(LAYOUT_BASE).forEach(function(k){ r[k] = LAYOUT_BASE[k]; });
    Object.keys(custom).forEach(function(k){ r[k] = custom[k]; });
    r.font = LAYOUT_BASE.font;
    r.paper_bgcolor = LAYOUT_BASE.paper_bgcolor;
    r.plot_bgcolor  = LAYOUT_BASE.plot_bgcolor;
    r.hoverlabel    = LAYOUT_BASE.hoverlabel;
    return r;
}