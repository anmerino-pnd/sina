import cv2
import json
from typing import List, Any

# Adjust these imports according to your actual project structure
from sina.config.paths import DATA

def hex_to_bgr(hex_color: str) -> tuple:
    """
    Converts a HEX color string (e.g., '#FF0000') to a BGR tuple for OpenCV (0, 0, 255).
    """
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (rgb[2], rgb[1], rgb[0])

def process_annotations(
        supermarket: str,
        city: str,
        date: str,
        image_name: str,
        bboxes: List[Any]
):
    image_path = DATA / supermarket / city / date / image_name

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at path: {image_path}")
    
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"OpenCV could not load the image: {image_path}")
        
    annotated_img = img.copy()
    base_name = image_path.stem  
    
    generated_crops = []

    for idx, box in enumerate(bboxes):
        label = box.label
        color_hex = getattr(box, 'color', '#00FF00') # Default to green if color is missing
        x, y, w, h = box.x, box.y, box.w, box.h
        
        # 1. CROP AND SAVE
        # OpenCV slicing uses format: [y:y+h, x:x+w]
        cropped_area = img[y:y+h, x:x+w]
        
        # Create subfolder for the specific class (e.g., /casa_ley/hermosillo/2026-02-26/recortes/)
        crop_dir = DATA / supermarket / city / date / "recortes"
        crop_dir.mkdir(parents=True, exist_ok=True)
        
        crop_filename = f"{base_name}_crop_{idx:03d}_{label}.jpg"
        crop_filepath = crop_dir / crop_filename
        
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
    annotated_dir = DATA / supermarket / city / date / "annotated" 
    annotated_dir.mkdir(parents=True, exist_ok=True)
    annotated_filepath = annotated_dir / f"{base_name}_annotated.jpg"
    cv2.imwrite(str(annotated_filepath), annotated_img)

    # 4. SAVE LABELS / COORDINATES AS JSON
    labels_dir = DATA / supermarket / city / date / "labels" 
    labels_dir.mkdir(parents=True, exist_ok=True)
    json_filepath = labels_dir / f"{base_name}.json"
    
    # Format data to save it
    boxes_dict = [b.dict() for b in bboxes]
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(boxes_dict, f, indent=4)

    return {
        "crops_saved": len(generated_crops),
        "annotated_image_path": str(annotated_filepath),
        "labels_file_path": str(json_filepath)
    }

