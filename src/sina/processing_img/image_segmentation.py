import cv2
import os
import json
from pathlib import Path
from typing import List, Dict, Any

# Adjust these imports according to your actual project structure
from sina.config.settings import DATA, DATASET_DIR, RECORTES_DIR, DATASET_ANNOTATED

def hex_to_bgr(hex_color: str) -> tuple:
    """
    Converts a HEX color string (e.g., '#FF0000') to a BGR tuple for OpenCV (0, 0, 255).
    """
    hex_color = hex_color.lstrip('#')
    # Convert to RGB integer tuple
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # OpenCV uses BGR format
    return (rgb[2], rgb[1], rgb[0])


def process_annotations(store_name: str, image_name: str, boxes: List[Any]) -> Dict[str, Any]:
    """
    Processes bounding boxes drawn by the frontend user.
    
    1. Opens the original image.
    2. Crops each annotated area and saves it into its respective class folder.
    3. Draws the bounding boxes on a copy of the image and saves it for visual reference.
    4. Saves the coordinates in a JSON file (YOLO/COCO style).
    
    Args:
        store_name (str): The name of the retailer (e.g., 'casa_ley', 'walmart').
        image_name (str): The specific filename (e.g., '2026-02-19_pagina_01.jpg').
        boxes (List[Any]): List of BoundingBox Pydantic models from the frontend.
        
    Returns:
        Dict: A summary of the generated files and crops.
    """
    
    # Construct paths dynamically based on store_name
    # Assuming your scraper saves images in: datos/{store_name}/{image_name}
    image_path = DATA / store_name / image_name 
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    # Load image using OpenCV
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"OpenCV could not load the image: {image_path}")
        
    annotated_img = img.copy()
    base_name = image_path.stem  # e.g., '2026-02-19_pagina_01'
    
    generated_crops = []

    # Process each bounding box drawn by the user
    for idx, box in enumerate(boxes):
        label = box.label
        color_hex = getattr(box, 'color', '#00FF00') # Default to green if color is missing
        x, y, w, h = box.x, box.y, box.w, box.h
        
        # 1. CROP AND SAVE
        # OpenCV slicing uses format: [y:y+h, x:x+w]
        cropped_area = img[y:y+h, x:x+w]
        
        # Create subfolder for the specific class (e.g., recortes/casa_ley/carnes/)
        class_dir = RECORTES_DIR / store_name / label
        class_dir.mkdir(parents=True, exist_ok=True)
        
        crop_filename = f"{base_name}_crop_{idx:03d}_{label}.jpg"
        crop_filepath = class_dir / crop_filename
        
        # Save crop (only if it has valid dimensions)
        if cropped_area.size > 0:
            cv2.imwrite(str(crop_filepath), cropped_area)
            generated_crops.append(str(crop_filepath))

        # 2. DRAW ON THE FULL ANNOTATED IMAGE
        bgr_color = hex_to_bgr(color_hex)
        
        # Draw rectangle
        cv2.rectangle(annotated_img, (x, y), (x+w, y+h), bgr_color, thickness=3)
        
        # Draw label text background and text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(label, font, 0.8, 2)[0]
        cv2.rectangle(annotated_img, (x, y - text_size[1] - 10), (x + text_size[0] + 10, y), bgr_color, -1)
        cv2.putText(annotated_img, label, (x + 5, y - 5), font, 0.8, (0, 0, 0), 2)

    # 3. SAVE FULL ANNOTATED IMAGE
    annotated_dir = DATASET_ANNOTATED / store_name
    annotated_dir.mkdir(parents=True, exist_ok=True)
    annotated_filepath = annotated_dir / f"{base_name}_annotated.jpg"
    cv2.imwrite(str(annotated_filepath), annotated_img)

    # 4. SAVE LABELS / COORDINATES AS JSON
    labels_dir = DATASET_DIR / "labels" / store_name
    labels_dir.mkdir(parents=True, exist_ok=True)
    json_filepath = labels_dir / f"{base_name}.json"
    
    # Format data to save it
    boxes_dict = [b.dict() for b in boxes]
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(boxes_dict, f, indent=4)

    return {
        "crops_saved": len(generated_crops),
        "annotated_image_path": str(annotated_filepath),
        "labels_file_path": str(json_filepath)
    }