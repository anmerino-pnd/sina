/**
 * SINA Annotator - Frontend Logic
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

// --- State Variables ---
let currentImg = new Image();
let isDrawing = false;
let startX = 0;
let startY = 0;

let activeLabel = 'otros';
let activeColor = '#ffffff';

let boundingBoxes = [];
let boxCounter = 0;

// Tool & Panning Variables
let currentTool = 'draw'; 
let isPanning = false;
let startPanX = 0;
let startPanY = 0;
let startScrollLeft = 0;
let startScrollTop = 0;

// NEW: Zoom Variables
let zoomLevel = 1.0;
const MIN_ZOOM = 0.2; // 20%
const MAX_ZOOM = 4.0; // 400%

// ==========================================
// 1. SCRAPER LOGIC
// ==========================================

function downloadFlyer() {
    const store = document.getElementById('scrapeStore').value;
    const city = document.getElementById('scrapeCity').value;
    
    if (!city.trim()) {
        alert("Por favor, ingresa una ciudad.");
        return;
    }

    const btn = document.getElementById('btnScrape');
    btn.disabled = true;
    btn.innerHTML = "⏳ Extrayendo... (Esto tomará unos segundos)";

    const payload = {
        supermarket: store,
        city: city,
        url: "" 
    };

    fetch('/sina/flyer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) throw new Error("Error HTTP " + response.status);
        return response.json();
    })
    .then(data => {
        alert(`¡Éxito! Folleto de ${store} en ${city} descargado correctamente.\n\nLa página se recargará.`);
        location.reload(); 
    })
    .catch(error => {
        console.error("Scraping Error:", error);
        alert("Ocurrió un error al intentar descargar el folleto. Revisa la consola o los logs del servidor.");
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = "📥 Descargar Ahora";
    });
}

// ==========================================
// 2. ZOOM & TOOL LOGIC
// ==========================================

function setTool(tool) {
    currentTool = tool;
    const btnDraw = document.getElementById('btnDraw');
    const btnPan = document.getElementById('btnPan');

    if (tool === 'draw') {
        canvas.style.cursor = 'crosshair';
        btnDraw.classList.add('active');
        btnPan.classList.remove('active');
    } else {
        canvas.style.cursor = 'grab';
        btnPan.classList.add('active');
        btnDraw.classList.remove('active');
    }
}

function changeZoom(delta) {
    setZoom(zoomLevel + delta);
}

function resetZoom() {
    setZoom(1.0);
}

function setZoom(newZoom) {
    if (!currentImg.src) return;
    
    // Clamp zoom between MIN and MAX
    zoomLevel = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));
    
    // Update UI label
    document.getElementById('zoomLabel').innerText = `${Math.round(zoomLevel * 100)}%`;
    
    // Resize the canvas physically via CSS. 
    // The scale mapping in the drawing logic automatically handles this change!
    canvas.style.width = `${currentImg.width * zoomLevel}px`;
    canvas.style.height = `${currentImg.height * zoomLevel}px`;
}

// Intercept Ctrl + Scroll to zoom the canvas instead of the browser page
canvasArea.addEventListener('wheel', (e) => {
    if (e.ctrlKey) {
        e.preventDefault(); // Stop entire browser from zooming
        const zoomDelta = e.deltaY > 0 ? -0.1 : 0.1;
        changeZoom(zoomDelta);
    }
}, { passive: false }); // passive: false is required to allow preventDefault()


// ==========================================
// 3. DYNAMIC DROPDOWN LOGIC
// ==========================================

window.onload = () => {
    Object.keys(FILE_TREE).forEach(store => {
        const formattedStore = store.toUpperCase().replace('_', ' ');
        storeSelect.add(new Option(formattedStore, store));
    });
};

storeSelect.addEventListener('change', (e) => {
    citySelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    dateSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    imageSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    
    citySelect.disabled = !e.target.value;
    dateSelect.disabled = true;
    imageSelect.disabled = true;

    if (e.target.value) {
        Object.keys(FILE_TREE[e.target.value]).forEach(city => {
            const formattedCity = city.toUpperCase().replace('_', ' ');
            citySelect.add(new Option(formattedCity, city));
        });
    }
});

citySelect.addEventListener('change', (e) => {
    dateSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    imageSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    
    dateSelect.disabled = !e.target.value;
    imageSelect.disabled = true;

    const store = storeSelect.value;
    if (e.target.value) {
        // --- NEW: Sort dates descending and keep top 10 ---
        let availableDates = Object.keys(FILE_TREE[store][e.target.value]);
        
        availableDates.sort((a, b) => b.localeCompare(a)); // Sort newest to oldest
        let top10Dates = availableDates.slice(0, 10);      // Take only the first 10
        
        top10Dates.forEach(date => {
            dateSelect.add(new Option(date, date));
        });
    }
});

dateSelect.addEventListener('change', (e) => {
    imageSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    imageSelect.disabled = !e.target.value;

    const store = storeSelect.value;
    const city = citySelect.value;
    if (e.target.value) {
        FILE_TREE[store][city][e.target.value].forEach(img => {
            imageSelect.add(new Option(img, img));
        });
    }
});

imageSelect.addEventListener('change', (e) => {
    const filename = e.target.value;
    if (!filename) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    document.getElementById('placeholder').style.display = 'none';

    const store = storeSelect.value;
    const city = citySelect.value;
    const date = dateSelect.value;
    
    currentImg.src = `/datos/${store}/${city}/${date}/${filename}`;

    currentImg.onload = () => {
        canvas.width = currentImg.width;
        canvas.height = currentImg.height;
        
        // Reset zoom to 100% when loading a new image
        resetZoom();
        
        redrawCanvas();
        boundingBoxes = []; 
        updateAnnotationList();
        
        // Reset scroll position
        canvasArea.scrollLeft = 0;
        canvasArea.scrollTop = 0;
    };
});

// ==========================================
// 4. CANVAS DRAWING & MOUSE EVENTS
// ==========================================

function setActiveClass(label, color) {
    activeLabel = label;
    activeColor = color;
    
    document.querySelectorAll('.class-btn').forEach(btn => {
        btn.classList.remove('active');
        if(btn.dataset.class === label) {
            btn.classList.add('active');
        }
    });
}

canvas.addEventListener('mousedown', (e) => {
    if (!currentImg.src) return;

    if (currentTool === 'pan') {
        isPanning = true;
        canvas.style.cursor = 'grabbing';
        startPanX = e.clientX;
        startPanY = e.clientY;
        startScrollLeft = canvasArea.scrollLeft;
        startScrollTop = canvasArea.scrollTop;
        return;
    }
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    startX = (e.clientX - rect.left) * scaleX;
    startY = (e.clientY - rect.top) * scaleY;
    isDrawing = true;
});

canvas.addEventListener('mousemove', (e) => {
    if (currentTool === 'pan' && isPanning) {
        const dx = e.clientX - startPanX;
        const dy = e.clientY - startPanY;
        canvasArea.scrollLeft = startScrollLeft - dx;
        canvasArea.scrollTop = startScrollTop - dy;
        return;
    }

    if (!isDrawing) return;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const currentX = (e.clientX - rect.left) * scaleX;
    const currentY = (e.clientY - rect.top) * scaleY;

    redrawCanvas();
    
    ctx.strokeStyle = activeColor;
    ctx.lineWidth = 3;
    ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
});

canvas.addEventListener('mouseup', (e) => {
    if (currentTool === 'pan') {
        isPanning = false;
        canvas.style.cursor = 'grab';
        return;
    }

    if (!isDrawing) return;
    isDrawing = false;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const endX = (e.clientX - rect.left) * scaleX;
    const endY = (e.clientY - rect.top) * scaleY;

    const boxX = Math.min(startX, endX);
    const boxY = Math.min(startY, endY);
    const boxW = Math.abs(endX - startX);
    const boxH = Math.abs(endY - startY);

    if (boxW > 10 && boxH > 10) {
        boxCounter++;
        boundingBoxes.push({
            id: boxCounter,
            label: activeLabel,
            color: activeColor,
            x: Math.round(boxX),
            y: Math.round(boxY),
            w: Math.round(boxW),
            h: Math.round(boxH)
        });
        updateAnnotationList();
    }
    
    redrawCanvas();
});

canvas.addEventListener('mouseleave', () => {
    if (isPanning) {
        isPanning = false;
        canvas.style.cursor = 'grab';
    }
});

function redrawCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (currentImg.src) {
        ctx.drawImage(currentImg, 0, 0, canvas.width, canvas.height);
    }

    boundingBoxes.forEach(box => {
        ctx.strokeStyle = box.color;
        ctx.lineWidth = 3;
        ctx.strokeRect(box.x, box.y, box.w, box.h);

        ctx.fillStyle = box.color;
        ctx.fillRect(box.x, box.y - 20, ctx.measureText(box.label).width + 10, 20);
        ctx.fillStyle = '#000000';
        ctx.font = '14px Arial';
        ctx.fillText(box.label, box.x + 5, box.y - 5);
    });
}

// ==========================================
// 5. API COMMUNICATION
// ==========================================

function updateAnnotationList() {
    annotList.innerHTML = '';
    document.getElementById('annotCount').innerText = boundingBoxes.length;

    boundingBoxes.forEach((box, index) => {
        const item = document.createElement('div');
        item.className = 'annot-item';
        item.innerHTML = `
            <div class="annot-label">
                <span class="color-dot" style="background-color: ${box.color}"></span>
                ${box.label} [${box.w}x${box.h}]
            </div>
            <button class="delete-btn" onclick="deleteBox(${index})">❌</button>
        `;
        annotList.appendChild(item);
    });
}

function deleteBox(index) {
    boundingBoxes.splice(index, 1);
    updateAnnotationList();
    redrawCanvas();
}

function clearAll() {
    boundingBoxes = [];
    updateAnnotationList();
    redrawCanvas();
}

function saveAll() {
    if (boundingBoxes.length === 0) {
        alert("Por favor dibuja al menos una anotación antes de guardar.");
        return;
    }

    const store = storeSelect.value;
    const city = citySelect.value;
    const date = dateSelect.value;
    const filename = imageSelect.value;

    if (!filename) return;

    const fullRelativePath = `${city}/${date}/${filename}`;

    const payload = {
        store_name: store, 
        image_filename: fullRelativePath,
        boxes: boundingBoxes
    };

    fetch('/sina/annotate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) throw new Error("Error en la respuesta del servidor");
        return response.json();
    })
    .then(data => {
        console.log("Success:", data);
        alert(`¡Guardado exitoso! Se generaron ${data.data.crops_saved} recortes.`);
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Ocurrió un error al guardar las anotaciones.");
    });
}