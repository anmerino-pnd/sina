/**
 * SINA Annotator - Frontend Logic
 * Handles dynamic dropdowns, canvas drawing, and API communication.
 */

// --- DOM Elements ---
const canvas = document.getElementById('annotCanvas');
const ctx = canvas.getContext('2d');
const annotList = document.getElementById('annotationList');

// Cascading Dropdowns
const storeSelect = document.getElementById('storeSelect');
const citySelect = document.getElementById('citySelect');
const dateSelect = document.getElementById('dateSelect');
const imageSelect = document.getElementById('imageSelect');

// State Variables
let currentImg = new Image();
let isDrawing = false;
let startX = 0;
let startY = 0;

// Default active class
let activeLabel = 'otros';
let activeColor = '#ffffff';

// Array to store our drawn bounding boxes
let boundingBoxes = [];
let boxCounter = 0;

// ==========================================
// 1. DYNAMIC DROPDOWN LOGIC
// ==========================================

// Populate Stores on window load
window.onload = () => {
    Object.keys(FILE_TREE).forEach(store => {
        // Format string for UI: "casa_ley" -> "CASA LEY"
        const formattedStore = store.toUpperCase().replace('_', ' ');
        storeSelect.add(new Option(formattedStore, store));
    });
};

// Store changes -> Populate Cities
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

// City changes -> Populate Dates
citySelect.addEventListener('change', (e) => {
    dateSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    imageSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
    
    dateSelect.disabled = !e.target.value;
    imageSelect.disabled = true;

    const store = storeSelect.value;
    if (e.target.value) {
        Object.keys(FILE_TREE[store][e.target.value]).forEach(date => {
            dateSelect.add(new Option(date, date));
        });
    }
});

// Date changes -> Populate Images
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

// Image changes -> Load into Canvas
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
    
    // Construct the exact path based on the user's filters
    currentImg.src = `/datos/${store}/${city}/${date}/${filename}`;

    currentImg.onload = () => {
        canvas.width = currentImg.width;
        canvas.height = currentImg.height;
        redrawCanvas();
        boundingBoxes = []; 
        updateAnnotationList();
    };
});

// ==========================================
// 2. CANVAS DRAWING LOGIC
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
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    startX = (e.clientX - rect.left) * scaleX;
    startY = (e.clientY - rect.top) * scaleY;
    isDrawing = true;
});

canvas.addEventListener('mousemove', (e) => {
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

    // Ignore accidental micro-clicks
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
// 3. UI UPDATES & API COMMUNICATION
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

    // Backend expects relative path from the store's root folder
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