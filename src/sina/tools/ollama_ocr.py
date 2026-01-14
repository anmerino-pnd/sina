import os
import cv2
import math
import ollama
import numpy as np
from PIL import Image

from sina.abstract_tools.supermarket_ocr import SupermarketOCRBase

class OllamaOCR(SupermarketOCRBase):
    def __init__(self, model: str):
        self.model = model

    def extract_text(self, image_path):
        return ollama.chat(
    model=self.model,
    messages=[
          {
              'role': 'system',
              'content': self.system_prompt,
              'role': 'user',
              'content': "Analiza este folleto y extrae todos los productos",
              'images': [image_path]  # 👈 lista de rutas de imagen
          }
      ],
    options={'temperature': 0, 'format': 'json'}
  )['message']['content']
    
    def smart_slicing(self, image_path, folder_path):
        """
        Divide una imagen en cuadrados calculando automáticamente el tamaño más eficiente.
        """
        img = Image.open(image_path)
        width, height = img.size
        base_name = os.path.splitext(os.path.basename(image_path))[0]

        # 1. calcular el divisor común más grande de width y height
        gcd = math.gcd(width, height)

        # 2. elegir tile_size:
        #    - si gcd es suficientemente grande, usarlo (división perfecta)
        #    - si no, aproximar usando la dimensión menor
        if gcd >= min(width, height) // 3:
            tile_size = gcd
        else:
            tile_size = min(width, height) // 2  # heurística: 2 cortes como mínimo

        # 3. calcular número de tiles
        n_cols = math.ceil(width / tile_size)
        n_rows = math.ceil(height / tile_size)

        tiles = []
        for row in range(n_rows):
            for col in range(n_cols):
                left = col * tile_size
                top = row * tile_size
                right = min(left + tile_size, width)
                bottom = min(top + tile_size, height)

                tile = img.crop((left, top, right, bottom))
                filename = f"{base_name}_r{row}_c{col}.png"
                path_out = os.path.join(folder_path, filename)
                tile.save(path_out, quality=100)
                tiles.append(path_out)

        return tiles

    def smart_crop(self, image_path, output_folder, min_area=5000):
        os.makedirs(output_folder, exist_ok=True)
        
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Binarización adaptativa
        thresh = cv2.adaptiveThreshold(gray, 255,
                                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 25, 15)

        # 2. Encontrar contornos
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        crops = []
        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)

            # 3. Filtrar contornos pequeños
            if w * h > min_area:
                crop = img[y:y+h, x:x+w]
                out_path = os.path.join(output_folder, f"crop_{i}.png")
                cv2.imwrite(out_path, crop)
                crops.append((x, y, w, h, out_path))
        
        return crops
        
    def smart_crop_auto_area(self, image_path, output_folder, area_ratio=0.01):
        """
        Recorta automáticamente bloques de una imagen de folleto usando OpenCV.
        `area_ratio` define el tamaño mínimo relativo del contorno respecto al área total.
        """        
        img = cv2.imread(image_path)
        height, width = img.shape[:2]
        total_area = width * height

        # Calculamos min_area dinámicamente
        min_area = total_area * area_ratio

        # Convertir a gris y binarizar
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 25, 15
        )

        # Encontrar contornos externos
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        crops = []
        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)

            if w * h >= min_area:
                crop = img[y:y+h, x:x+w]
                out_path = os.path.join(output_folder, f"crop_{i}.png")
                cv2.imwrite(out_path, crop)
                crops.append((x, y, w, h, out_path))
        
        return crops

    def _merge_rects(self, rects, threshold=50):
        """
        Helper function to merge overlapping or nearby rectangles.
        """
        while True:
            merged_one = False
            merged_rects = []
            while rects:
                r1 = rects.pop(0)
                x1, y1, w1, h1 = r1
                merged = False
                # Iterate over remaining rects to check for merges
                for i in range(len(rects) - 1, -1, -1):
                    r2 = rects[i]
                    x2, y2, w2, h2 = r2
                    # Create expanded rect for proximity check
                    exp_x1, exp_y1 = max(0, x1 - threshold), max(0, y1 - threshold)
                    exp_w1, exp_h1 = w1 + 2 * threshold, h1 + 2 * threshold
                    
                    # Check for intersection between expanded r1 and r2
                    if not (exp_x1 > x2 + w2 or exp_x1 + exp_w1 < x2 or exp_y1 > y2 + h2 or exp_y1 + exp_h1 < y2):
                        # Merge them
                        min_x = min(x1, x2)
                        min_y = min(y1, y2)
                        max_x = max(x1 + w1, x2 + w2)
                        max_y = max(y1 + h1, y2 + h2)
                        merged_rects.append((min_x, min_y, max_x - min_x, max_y - min_y))
                        rects.pop(i)
                        merged = True
                        merged_one = True
                        break # r1 is merged, break inner loop
                if not merged:
                    merged_rects.append(r1)
            rects = merged_rects
            if not merged_one:
                break
        return rects
    
    def crop_by_zones(self, image_path, output_folder, min_area_ratio=0.005, padding=15):
        """
        Intelligently finds and crops logical zones from a flyer image.
        """
        os.makedirs(output_folder, exist_ok=True)
        
        # 1. Pre-processing
        img = cv2.imread(image_path)
        original_img = img.copy() # Keep a color copy for the final crop
        total_area = img.shape[0] * img.shape[1]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Blur to reduce noise and help merge nearby elements
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        # Adaptive thresholding is great for uneven lighting
        thresh = cv2.adaptiveThreshold(blurred, 255, 
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY_INV, 11, 4)

        # 2. Contour Detection
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 3. Filtering and Grouping
        initial_rects = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter out very small contours (noise)
            if w * h > total_area * min_area_ratio:
                initial_rects.append((x, y, w, h))

        # The magic step: merge nearby rectangles into logical zones
        merged_zones = self._merge_rects(initial_rects)

        # 4. Cropping and Saving
        cropped_images_paths = []
        for i, (x, y, w, h) in enumerate(merged_zones):
            # Add some padding to the crop
            x_pad = max(0, x - padding)
            y_pad = max(0, y - padding)
            w_pad = min(img.shape[1], x + w + padding) - x_pad
            h_pad = min(img.shape[0], y + h + padding) - y_pad

            # Crop from the original color image
            crop = original_img[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
            
            # Save the cropped image
            out_path = os.path.join(output_folder, f"zone_{i+1:02d}.jpg")
            cv2.imwrite(out_path, crop)
            cropped_images_paths.append(out_path)
            
        print(f"Successfully cropped {len(cropped_images_paths)} zones.")
        return cropped_images_paths