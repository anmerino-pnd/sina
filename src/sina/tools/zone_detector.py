import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance

class SmartFlyerDetector:
    """
    Detector híbrido que usa CLAHE + detección de espacios blancos
    para recortar folletos de supermercado de forma inteligente.
    """
    
    def __init__(self, 
                 method='whitespace',
                 min_zone_height_percent=5,
                 min_zone_width_percent=15,
                 padding_percent=3,
                 whitespace_threshold=240):
        """
        Args:
            method: 'whitespace' (detecta espacios blancos) o 'hierarchical' (columnas+subdivisiones)
            min_zone_height_percent: Altura mínima de zona (% de altura total)
            min_zone_width_percent: Ancho mínimo de zona (% de ancho total)
            padding_percent: Padding arriba/abajo (%)
            whitespace_threshold: Umbral para considerar "blanco" (0-255)
        """
        self.method = method
        self.min_zone_height_percent = min_zone_height_percent
        self.min_zone_width_percent = min_zone_width_percent
        self.padding_percent = padding_percent
        self.whitespace_threshold = whitespace_threshold

    def detect_zones(self, image_path, output_folder, debug=False):
        """
        Detecta zonas usando el método configurado o el modo automático.
        """        
        os.makedirs(output_folder, exist_ok=True)
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"No se pudo cargar: {image_path}")
        
        h, w = img.shape[:2]
        print(f"📸 Imagen cargada: {w}x{h}px")
        
        # --- NUEVO: MODO AUTOMÁTICO ---
        if self.method == 'auto':
            print("\n🤖 Modo automático: evaluando mejor estrategia...")
            zones_whitespace = self._detect_by_whitespace(img, output_folder, debug=False)
            zones_hierarchical = self._detect_hierarchical(img, output_folder, debug=False)
            
            count_ws = len(zones_whitespace)
            count_hier = len(zones_hierarchical)
            
            print(f"   → whitespace: {count_ws} zonas")
            print(f"   → hierarchical: {count_hier} zonas")

            # Decisión inteligente:
            target_range = range(3, 7)
            best_method = None

            if count_ws in target_range and count_hier not in target_range:
                best_method = 'whitespace'
            elif count_hier in target_range and count_ws not in target_range:
                best_method = 'hierarchical'
            elif count_ws in target_range and count_hier in target_range:
                best_method = 'hierarchical' if abs(count_hier - 5) < abs(count_ws - 5) else 'whitespace'
            else:
                # Si ninguno cae en el rango, elegir el que más se acerque a 4-5
                best_method = 'hierarchical' if abs(count_hier - 5) < abs(count_ws - 5) else 'whitespace'

            print(f"✅ Método elegido: {best_method.upper()}")
            zones = zones_hierarchical if best_method == 'hierarchical' else zones_whitespace
        
        # --- Modos normales ---
        elif self.method == 'whitespace':
            zones = self._detect_by_whitespace(img, output_folder, debug)
        elif self.method == 'hierarchical':
            zones = self._detect_hierarchical(img, output_folder, debug)
        else:
            raise ValueError(f"Método desconocido: {self.method}")
        
        # --- Aplicar padding y recortar ---
        final_zones = self._apply_padding_and_crop(img, zones, output_folder, debug)
        
        print(f"\n✅ Total: {len(final_zones)} zonas detectadas y guardadas")
        return final_zones

    
    # def detect_zones(self, image_path, output_folder, debug=False):
    #     """
    #     Detecta zonas usando el método configurado.
    #     """        
    #     os.makedirs(output_folder, exist_ok=True)
    #     img = cv2.imread(image_path)
    #     if img is None:
    #         raise FileNotFoundError(f"No se pudo cargar: {image_path}")
        
    #     h, w = img.shape[:2]
    #     print(f"📸 Imagen cargada: {w}x{h}px")
        
    #     if self.method == 'whitespace':
    #         zones = self._detect_by_whitespace(img, output_folder, debug)
    #     elif self.method == 'hierarchical':
    #         zones = self._detect_hierarchical(img, output_folder, debug)
    #     else:
    #         raise ValueError(f"Método desconocido: {self.method}")
        
    #     # Aplicar padding y recortar
    #     final_zones = self._apply_padding_and_crop(img, zones, output_folder, debug)
        
    #     print(f"\n✅ Total: {len(final_zones)} zonas detectadas y guardadas")
    #     return final_zones
    
    def _detect_by_whitespace(self, img, output_folder, debug):
        """
        Detecta zonas basándose en espacios blancos horizontales.
        Perfecto para folletos con separadores blancos naturales.
        """
        h, w = img.shape[:2]
        print(f"\n🔍 Método: Detección por espacios blancos...")
        
        # === PREPROCESAMIENTO AVANZADO ===
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # CLAHE para mejorar contraste
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Filtro bilateral para preservar bordes
        bilateral = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        if debug:
            cv2.imwrite(os.path.join(output_folder, "1_preprocessed_clahe.jpg"), enhanced)
            cv2.imwrite(os.path.join(output_folder, "1_preprocessed_bilateral.jpg"), bilateral)
        
        # === DETECCIÓN DE ESPACIOS BLANCOS ===
        # Proyección horizontal: contar píxeles blancos por fila
        white_threshold = self.whitespace_threshold
        h_projection = np.sum(bilateral > white_threshold, axis=1) / w * 100  # % de blancos
        
        if debug:
            self._save_projection_plot(h_projection, output_folder, 
                                      "Detección de Espacios Blancos Horizontales",
                                      threshold=70)
        
        # Encontrar filas que son mayormente blancas (>70% blanco)
        whitespace_rows = h_projection > 70
        
        # Detectar bloques continuos de contenido
        content_blocks = []
        in_content = False
        block_start = 0
        
        for i, is_white in enumerate(whitespace_rows):
            if not is_white and not in_content:
                # Inicio de bloque de contenido
                block_start = i
                in_content = True
            elif is_white and in_content:
                # Fin de bloque de contenido
                block_end = i
                block_height = block_end - block_start
                
                # Filtrar bloques muy pequeños
                if block_height > h * (self.min_zone_height_percent / 100):
                    content_blocks.append((0, block_start, w, block_height))
                
                in_content = False
        
        # No olvidar el último bloque si llega hasta el final
        if in_content:
            block_height = h - block_start
            if block_height > h * (self.min_zone_height_percent / 100):
                content_blocks.append((0, block_start, w, block_height))
        
        print(f"   ✓ {len(content_blocks)} bloques de contenido detectados")
        
        # Si no se detectaron bloques, subdividir cada bloque verticalmente
        if len(content_blocks) < 2:
            print("   ⚠️ Pocos bloques horizontales, aplicando subdivisión vertical...")
            zones = self._subdivide_blocks_vertically(img, content_blocks)
        else:
            zones = content_blocks
        
        return zones
    
    def _subdivide_blocks_vertically(self, img, blocks):
        """
        Subdivide bloques grandes verticalmente (detecta columnas).
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        all_zones = []
        
        for block_x, block_y, block_w, block_h in blocks:
            # Extraer región del bloque
            block_region = gray[block_y:block_y+block_h, block_x:block_x+block_w]
            
            # Proyección vertical en este bloque
            v_projection = np.sum(block_region > self.whitespace_threshold, axis=0) / block_h * 100
            
            # Detectar columnas (zonas con mucho blanco vertical)
            whitespace_cols = v_projection > 60
            
            # Encontrar separadores verticales
            columns = []
            in_content = False
            col_start = 0
            
            for i, is_white in enumerate(whitespace_cols):
                if not is_white and not in_content:
                    col_start = i
                    in_content = True
                elif is_white and in_content:
                    col_width = i - col_start
                    if col_width > w * (self.min_zone_width_percent / 100):
                        columns.append((block_x + col_start, block_y, col_width, block_h))
                    in_content = False
            
            # Última columna
            if in_content:
                col_width = block_w - col_start
                if col_width > w * (self.min_zone_width_percent / 100):
                    columns.append((block_x + col_start, block_y, col_width, block_h))
            
            # Si no hay columnas claras, usar el bloque completo
            if len(columns) == 0:
                all_zones.append((block_x, block_y, block_w, block_h))
            else:
                all_zones.extend(columns)
        
        return all_zones
    
    def _detect_hierarchical(self, img, output_folder, debug):
        """
        Método jerárquico original (columnas + subdivisiones).
        """
        h, w = img.shape[:2]
        print(f"\n🔍 Método: Jerárquico (columnas + subdivisiones)...")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Mejorar con CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        if debug:
            cv2.imwrite(os.path.join(output_folder, "1_preprocessed.jpg"), enhanced)
        
        # Detectar columnas (proyección vertical)
        v_projection = np.sum(enhanced < 200, axis=0)
        v_projection_smooth = np.convolve(v_projection, np.ones(w//50)//(w//50), mode='same')
        v_threshold = np.max(v_projection_smooth) * 0.12
        
        gaps_v = self._find_gaps(v_projection_smooth, v_threshold, min_gap_size=w//30)
        x_splits = [0] + gaps_v + [w]
        
        if len(x_splits) == 2:
            x_splits = [0, w//2, w]
        
        # Crear columnas
        columns = []
        for i in range(len(x_splits) - 1):
            x1, x2 = x_splits[i], x_splits[i + 1]
            columns.append((x1, 0, x2 - x1, h))
        
        # Subdividir cada columna horizontalmente
        all_zones = []
        for col_x, col_y, col_w, col_h in columns:
            col_region = enhanced[col_y:col_y+col_h, col_x:col_x+col_w]
            
            h_projection = np.sum(col_region < 200, axis=1)
            h_projection_smooth = np.convolve(h_projection, np.ones(max(5, col_h//100))//max(5, col_h//100), mode='same')
            h_threshold = np.max(h_projection_smooth) * 0.08
            
            gaps_h = self._find_gaps(h_projection_smooth, h_threshold, min_gap_size=col_h//25)
            y_splits = [0] + gaps_h + [col_h]
            
            # Limitar subdivisiones
            if len(y_splits) > 5:
                indices = np.linspace(0, len(y_splits) - 1, 4, dtype=int)
                y_splits = [y_splits[i] for i in indices]
            
            for j in range(len(y_splits) - 1):
                y1, y2 = y_splits[j], y_splits[j + 1]
                zone_h = y2 - y1
                
                if zone_h > h * (self.min_zone_height_percent / 100):
                    all_zones.append((col_x, col_y + y1, col_w, zone_h))
        
        return all_zones
    
    def _find_gaps(self, projection, threshold, min_gap_size):
        """Encuentra espacios vacíos."""
        below_threshold = projection < threshold
        gaps = []
        in_gap = False
        gap_start = 0
        
        for i, is_gap in enumerate(below_threshold):
            if is_gap and not in_gap:
                gap_start = i
                in_gap = True
            elif not is_gap and in_gap:
                if i - gap_start >= min_gap_size:
                    gaps.append((gap_start + i) // 2)
                in_gap = False
        
        return gaps
    
    def _apply_padding_and_crop(self, img, zones, output_folder, debug):
        """Aplica padding y guarda los recortes."""
        h, w = img.shape[:2]
        final_zones = []
        
        for i, (x, y, zone_w, zone_h) in enumerate(zones, 1):
            # Calcular padding
            padding_top = int(zone_h * self.padding_percent / 100)
            padding_bottom = int(zone_h * self.padding_percent / 100)
            padding_left = int(zone_w * self.padding_percent / 100)
            padding_right = int(zone_w * self.padding_percent / 100)
            
            # Aplicar padding sin salir de la imagen
            y_start = max(0, y - padding_top)
            y_end = min(h, y + zone_h + padding_bottom)
            x_start = max(0, x - padding_left)
            x_end = min(w, x + zone_w + padding_right)
            
            # Recortar
            crop = img[y_start:y_end, x_start:x_end]
            
            # Guardar
            out_path = os.path.join(output_folder, f"zone_{i:02d}.jpg")
            cv2.imwrite(out_path, crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            final_zones.append({
                'id': i,
                'x': x_start,
                'y': y_start,
                'width': x_end - x_start,
                'height': y_end - y_start,
                'path': out_path,
                'original_bounds': (x, y, zone_w, zone_h)
            })
        
        # Visualización
        if debug:
            self._create_debug_visualization(img, final_zones, output_folder)
        
        return final_zones
    
    def _save_projection_plot(self, projection, output_folder, title, threshold=None):
        """Guarda gráfica de proyección."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(15, 6))
            plt.plot(projection, linewidth=2, color='#2E86AB')
            
            if threshold:
                plt.axhline(y=threshold, color='#A23B72', linestyle='--', 
                           linewidth=2, label=f'Umbral ({threshold}%)')
            
            plt.title(title, fontsize=13, fontweight='bold')
            plt.xlabel('Posición (píxeles)', fontsize=11)
            plt.ylabel('% Píxeles Blancos', fontsize=11)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            
            plt.savefig(os.path.join(output_folder, "2_whitespace_projection.png"), 
                       dpi=120, bbox_inches='tight')
            plt.close()
        except ImportError:
            pass
    
    def _create_debug_visualization(self, img, zones, output_folder):
        """Visualización final."""
        debug_img = img.copy()
        
        colors = [(255, 50, 50), (50, 255, 50), (50, 50, 255), 
                 (255, 255, 50), (255, 50, 255), (50, 255, 255)]
        
        for zone in zones:
            color = colors[(zone['id'] - 1) % len(colors)]
            x, y = zone['x'], zone['y']
            w, h = zone['width'], zone['height']
            
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), color, 5)
            cv2.putText(debug_img, f"Z{zone['id']}", (x + 15, y + 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 4)
        
        cv2.imwrite(os.path.join(output_folder, "3_final_zones.jpg"), debug_img)
        print(f"📊 Visualización guardada: 3_final_zones.jpg")


