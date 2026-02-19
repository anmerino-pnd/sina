/**
 * SINA Annotator - Frontend Logic
 * Handles canvas drawing, bounding box management, and API communication.
 */

// --- Global Variables ---
const canvas = document.getElementById('annotCanvas');
const ctx = canvas.getContext('2d');
const imageSelect = document.getElementById('imageSelect');
const annotList = document.getElementById('annotationList');

let currentImg = new Image();
let isDrawing = false;
let startX = 0;
let startY = 0;

// Default active class (will be updated when user clicks a tag button)
let activeLabel = 'otros';
let activeColor = '#ffffff';

// Array to store our drawn bounding boxes
// Format: { id: number, label: str, color: str, x: number, y: number, w: number, h: number }
let boundingBoxes = [];
let boxCounter = 0;

// --- Initialization ---

// Update active class when a label button is clicked in the UI
function setActiveClass(label, color) {
    activeLabel = label;
    activeColor = color;
    
    // Update UI buttons visual state
    document.querySelectorAll('.class-btn').forEach(btn => {
        btn.classList.remove('active');
        if(btn.dataset.class === label) {
            btn.classList.add('active');
        }
    });
}

// Load image into canvas when selected from dropdown
imageSelect.addEventListener('change', (e) => {
    const filename = e.target.value;
    if (!filename) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    // Hide placeholder
    document.getElementById('placeholder').style.display = 'none';

    // Construct image URL (adjust this to match your FastAPI static mounting)
    // Assuming the API serves the image from /datos/{store_name}/...
    // For now, testing with a direct static path format:
    const storeName = "casa_ley"; // This can also be dynamic from the UI
    currentImg.src = `/datos/${storeName}/${filename}`;

    currentImg.onload = () => {
        // Resize canvas to match image dimensions
        canvas.width = currentImg.width;
        canvas.height = currentImg.height;
        redrawCanvas();
        boundingBoxes = []; // Clear previous annotations
        updateAnnotationList();
    };
});

// --- Mouse Events for Drawing ---

canvas.addEventListener('mousedown', (e) => {
    if (!currentImg.src) return;
    
    const rect = canvas.getBoundingClientRect();
    // Calculate scale in case the canvas is scaled via CSS
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

    // Constantly redraw the image, previous boxes, and the current drawing box
    redrawCanvas();
    
    // Draw the active box
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

    // Calculate final x, y, width, height (handling negative drag directions)
    const boxX = Math.min(startX, endX);
    const boxY = Math.min(startY, endY);
    const boxW = Math.abs(endX - startX);
    const boxH = Math.abs(endY - startY);

    // Ignore tiny accidental clicks
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

// --- Core Functions ---

function redrawCanvas() {
    // Clear and draw image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (currentImg.src) {
        ctx.drawImage(currentImg, 0, 0, canvas.width, canvas.height);
    }

    // Draw all saved bounding boxes
    boundingBoxes.forEach(box => {
        ctx.strokeStyle = box.color;
        ctx.lineWidth = 3;
        ctx.strokeRect(box.x, box.y, box.w, box.h);

        // Draw label background and text
        ctx.fillStyle = box.color;
        ctx.fillRect(box.x, box.y - 20, ctx.measureText(box.label).width + 10, 20);
        ctx.fillStyle = '#000000'; // Black text for contrast
        ctx.font = '14px Arial';
        ctx.fillText(box.label, box.x + 5, box.y - 5);
    });
}

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

// --- API Communication ---

function saveAll() {
    if (boundingBoxes.length === 0) {
        alert("Please draw at least one bounding box before saving.");
        return;
    }

    const filename = imageSelect.value;
    if (!filename) return;

    // Hardcoding store_name for now, but ideally this comes from a UI selector
    const payload = {
        store_name: "casa_ley", 
        image_filename: filename,
        boxes: boundingBoxes
    };

    fetch('/api/annotate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        console.log("Success:", data);
        alert(`Successfully saved and cropped ${data.data.crops_saved} images!`);
    })
    .catch(error => {
        console.error("Error:", error);
        alert("An error occurred while saving annotations.");
    });
}

function clearAll() {
    boundingBoxes = [];
    updateAnnotationList();
    redrawCanvas();
}