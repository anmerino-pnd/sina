import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from scipy.ndimage import label as scipy_label

class UltimateFlyerDetector:
    """
    Detector inteligente y adaptativo para folletos de supermercado.
    Combina análisis de orientación + whitespace + hierarchical + clustering.
    """
    
    def __init__(self, 
                 use_clustering=True,
                 clustering_method='dbscan',
                 target_zones='auto',
                 padding_percent=4,
                 min_zone_area_percent=2):
        """
        Args:
            use_clustering: Activar refinamiento con clustering
            clustering_method: 'dbscan', 'kmeans', 'hierarchical'
            target_zones: 'auto' o número aproximado de zonas deseadas
            padding_percent: Padding para los recortes (%)
            min_zone_area_percent: Área mínima de zona válida (% del total)
        """
        self.use_clustering = use_clustering
        self.clustering_method = clustering_method
        self.target_zones = target_zones
        self.padding_percent = padding_percent
        self.min_zone_area_percent = min_zone_area_percent
    
    def detect_zones(self, image_path, output_folder, debug=False):
        """
        Pipeline completo de detección adaptativa.
        """
        os.makedirs(output_folder, exist_ok=True)
        
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"No se pudo cargar: {image_path}")
        
        h, w = img.shape[:2]
        aspect_ratio = w / h
        
        print("=" * 70)
        print(f"📸 Imagen: {w}x{h}px (ratio: {aspect_ratio:.2f})")
        print("=" * 70)
        
        # FASE 1: Análisis de orientación y preprocesamiento
        strategy = self._determine_strategy(aspect_ratio)
        print(f"\n🧠 Estrategia: {strategy}")
        
        gray = self._advanced_preprocessing(img, output_folder, debug)
        
        # FASE 2: Detección primaria según orientación
        primary_zones = self._primary_detection(img, gray, strategy, output_folder, debug)
        print(f"   ✓ {len(primary_zones)} zonas primarias detectadas")
        
        # FASE 3: Subdivisión inteligente
        subdivided_zones = self._intelligent_subdivision(img, gray, primary_zones, 
                                                         strategy, output_folder, debug)
        print(f"   ✓ {len(subdivided_zones)} zonas tras subdivisión")
        
        # FASE 4: Refinamiento con clustering (opcional)
        if self.use_clustering:
            refined_zones = self._clustering_refinement(img, gray, subdivided_zones, 
                                                        output_folder, debug)
            print(f"   ✓ {len(refined_zones)} zonas tras clustering")
        else:
            refined_zones = subdivided_zones
        
        # FASE 5: Filtrado, fusión y limpieza
        clean_zones = self._cleanup_zones(refined_zones, w, h)
        print(f"   ✓ {len(clean_zones)} zonas finales tras limpieza")
        
        # FASE 6: Aplicar padding y guardar
        final_zones = self._save_zones(img, clean_zones, output_folder, debug)
        
        print(f"\n✅ COMPLETADO: {len(final_zones)} zonas listas")
        return final_zones
    
    def _determine_strategy(self, aspect_ratio):
        """Determina estrategia basada en orientación."""
        if aspect_ratio > 1.3:
            return "HORIZONTAL_FIRST"  # Ancho > Alto → columnas primero
        elif aspect_ratio < 0.75:
            return "VERTICAL_FIRST"    # Alto > Ancho → filas primero
        else:
            return "ADAPTIVE"          # Cuadrado → analizar densidad
    
    def _advanced_preprocessing(self, img, output_folder, debug):
        """Preprocesamiento con CLAHE + bilateral."""
        print("\n🔧 Preprocesamiento...")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # CLAHE para contraste local
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Filtro bilateral para preservar bordes
        bilateral = cv2.bilateralFilter(enhanced, 11, 80, 80)
        
        if debug:
            cv2.imwrite(os.path.join(output_folder, "1_preprocessed.jpg"), bilateral)
        
        return bilateral
    
    def _primary_detection(self, img, gray, strategy, output_folder, debug):
        """Detección primaria según estrategia."""
        h, w = img.shape[:2]
        
        print(f"\n🔍 Fase 1: Detección primaria ({strategy})...")
        
        if strategy == "HORIZONTAL_FIRST":
            # Detectar columnas verticales primero
            zones = self._detect_vertical_divisions(gray, w, h, output_folder, debug)
            
        elif strategy == "VERTICAL_FIRST":
            # Detectar franjas horizontales primero
            zones = self._detect_horizontal_divisions(gray, w, h, output_folder, debug)
            
        else:  # ADAPTIVE
            # Analizar qué eje tiene más separadores
            h_gaps = self._count_gaps_horizontal(gray, h, w)
            v_gaps = self._count_gaps_vertical(gray, w, h)
            
            print(f"   📊 Gaps horizontales: {h_gaps}, verticales: {v_gaps}")
            
            if v_gaps > h_gaps:
                zones = self._detect_vertical_divisions(gray, w, h, output_folder, debug)
            else:
                zones = self._detect_horizontal_divisions(gray, w, h, output_folder, debug)
        
        return zones
    
    def _detect_vertical_divisions(self, gray, w, h, output_folder, debug):
        """Detecta columnas verticales (proyección vertical)."""
        print("   → Detectando columnas verticales...")
        
        # Proyección vertical: contar píxeles blancos por columna
        v_projection = np.sum(gray > 240, axis=0) / h * 100
        
        # Suavizar
        window = max(5, w // 50)
        v_smooth = np.convolve(v_projection, np.ones(window) / window, mode='same')
        
        if debug:
            self._save_projection(v_smooth, "vertical", 70, output_folder)
        
        # Detectar gaps (columnas con >70% blanco)
        gaps = self._find_continuous_gaps(v_smooth > 70, min_gap_size=w // 40)
        
        # Crear divisiones
        x_splits = [0] + gaps + [w]
        
        if len(x_splits) == 2:  # No se detectaron columnas
            x_splits = [0, w // 2, w]
        
        zones = []
        for i in range(len(x_splits) - 1):
            x1, x2 = x_splits[i], x_splits[i + 1]
            zones.append({'x': x1, 'y': 0, 'w': x2 - x1, 'h': h})
        
        return zones
    
    def _detect_horizontal_divisions(self, gray, w, h, output_folder, debug):
        """Detecta franjas horizontales (proyección horizontal)."""
        print("   → Detectando franjas horizontales...")
        
        # Proyección horizontal
        h_projection = np.sum(gray > 240, axis=1) / w * 100
        
        # Suavizar
        window = max(5, h // 50)
        h_smooth = np.convolve(h_projection, np.ones(window) / window, mode='same')
        
        if debug:
            self._save_projection(h_smooth, "horizontal", 70, output_folder)
        
        # Detectar gaps
        gaps = self._find_continuous_gaps(h_smooth > 70, min_gap_size=h // 40)
        
        # Crear divisiones
        y_splits = [0] + gaps + [h]
        
        if len(y_splits) == 2:
            y_splits = [0, h // 2, h]
        
        zones = []
        for i in range(len(y_splits) - 1):
            y1, y2 = y_splits[i], y_splits[i + 1]
            zones.append({'x': 0, 'y': y1, 'w': w, 'h': y2 - y1})
        
        return zones
    
    def _count_gaps_horizontal(self, gray, h, w):
        """Cuenta cuántos gaps horizontales hay."""
        h_projection = np.sum(gray > 240, axis=1) / w * 100
        return np.sum((h_projection > 70)[:-1] != (h_projection > 70)[1:])
    
    def _count_gaps_vertical(self, gray, w, h):
        """Cuenta cuántos gaps verticales hay."""
        v_projection = np.sum(gray > 240, axis=0) / h * 100
        return np.sum((v_projection > 70)[:-1] != (v_projection > 70)[1:])
    
    def _intelligent_subdivision(self, img, gray, primary_zones, strategy, 
                                 output_folder, debug):
        """Subdivide zonas grandes en el eje complementario."""
        print(f"\n🔍 Fase 2: Subdivisión inteligente...")
        
        h, w = img.shape[:2]
        all_zones = []
        
        for idx, zone in enumerate(primary_zones):
            zx, zy, zw, zh = zone['x'], zone['y'], zone['w'], zone['h']
            
            # Extraer región
            region = gray[zy:zy+zh, zx:zx+zw]
            
            # Subdividir en el eje complementario
            if strategy in ["HORIZONTAL_FIRST", "ADAPTIVE"]:
                # Ya tenemos columnas, subdividir horizontalmente
                sub_zones = self._subdivide_horizontal(region, zx, zy, zw, zh)
            else:
                # Ya tenemos filas, subdividir verticalmente
                sub_zones = self._subdivide_vertical(region, zx, zy, zw, zh)
            
            all_zones.extend(sub_zones)
        
        return all_zones
    
    def _subdivide_horizontal(self, region, offset_x, offset_y, zw, zh):
        """Subdivide una columna horizontalmente."""
        h_projection = np.sum(region > 240, axis=1) / zw * 100
        window = max(3, zh // 30)
        h_smooth = np.convolve(h_projection, np.ones(window) / window, mode='same')
        
        gaps = self._find_continuous_gaps(h_smooth > 65, min_gap_size=zh // 25)
        y_splits = [0] + gaps + [zh]
        
        # Limitar subdivisiones
        if len(y_splits) > 6:
            indices = np.linspace(0, len(y_splits) - 1, 5, dtype=int)
            y_splits = [y_splits[i] for i in indices]
        
        zones = []
        for i in range(len(y_splits) - 1):
            y1, y2 = y_splits[i], y_splits[i + 1]
            if (y2 - y1) > zh * 0.05:  # Filtrar muy pequeñas
                zones.append({
                    'x': offset_x,
                    'y': offset_y + y1,
                    'w': zw,
                    'h': y2 - y1
                })
        
        return zones if zones else [{'x': offset_x, 'y': offset_y, 'w': zw, 'h': zh}]
    
    def _subdivide_vertical(self, region, offset_x, offset_y, zw, zh):
        """Subdivide una fila verticalmente."""
        v_projection = np.sum(region > 240, axis=0) / zh * 100
        window = max(3, zw // 30)
        v_smooth = np.convolve(v_projection, np.ones(window) / window, mode='same')
        
        gaps = self._find_continuous_gaps(v_smooth > 65, min_gap_size=zw // 25)
        x_splits = [0] + gaps + [zw]
        
        if len(x_splits) > 6:
            indices = np.linspace(0, len(x_splits) - 1, 5, dtype=int)
            x_splits = [x_splits[i] for i in indices]
        
        zones = []
        for i in range(len(x_splits) - 1):
            x1, x2 = x_splits[i], x_splits[i + 1]
            if (x2 - x1) > zw * 0.1:
                zones.append({
                    'x': offset_x + x1,
                    'y': offset_y,
                    'w': x2 - x1,
                    'h': zh
                })
        
        return zones if zones else [{'x': offset_x, 'y': offset_y, 'w': zw, 'h': zh}]
    
    def _clustering_refinement(self, img, gray, zones, output_folder, debug):
        """Refinamiento con clustering de contenido."""
        print(f"\n🎯 Fase 3: Clustering ({self.clustering_method})...")
        
        h, w = img.shape[:2]
        
        # Binarización para encontrar contenido
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Encontrar píxeles de contenido
        content_pixels = np.column_stack(np.where(binary > 0))
        
        if len(content_pixels) < 100:
            print("   ⚠️ Muy poco contenido, saltando clustering")
            return zones
        
        # Limitar número de píxeles para eficiencia
        if len(content_pixels) > 50000:
            indices = np.random.choice(len(content_pixels), 50000, replace=False)
            content_pixels = content_pixels[indices]
        
        # Aplicar clustering
        if self.clustering_method == 'dbscan':
            clusters = self._dbscan_clustering(content_pixels, h, w)
        elif self.clustering_method == 'kmeans':
            n_clusters = len(zones) if self.target_zones == 'auto' else self.target_zones
            clusters = self._kmeans_clustering(content_pixels, n_clusters)
        else:
            return zones
        
        # Convertir clusters a bounding boxes
        cluster_zones = self._clusters_to_zones(content_pixels, clusters, h, w)
        
        if debug:
            self._visualize_clusters(img, content_pixels, clusters, output_folder)
        
        print(f"   ✓ {len(cluster_zones)} clusters detectados")
        
        # Fusionar con zonas existentes
        return self._merge_zone_sets(zones, cluster_zones, w, h)
    
    def _dbscan_clustering(self, pixels, h, w):
        """Clustering con DBSCAN."""
        # Normalizar coordenadas
        scaler = StandardScaler()
        pixels_scaled = scaler.fit_transform(pixels)
        
        # DBSCAN
        eps = 0.15  # Ajusta según densidad
        min_samples = 30
        
        db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
        labels = db.fit_predict(pixels_scaled)
        
        return labels
    
    def _kmeans_clustering(self, pixels, n_clusters):
        """Clustering con K-Means."""
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(pixels)
        return labels
    
    def _clusters_to_zones(self, pixels, labels, h, w):
        """Convierte clusters a bounding boxes."""
        zones = []
        
        for cluster_id in set(labels):
            if cluster_id == -1:  # Ruido en DBSCAN
                continue
            
            cluster_points = pixels[labels == cluster_id]
            
            if len(cluster_points) < 50:
                continue
            
            y_min, x_min = cluster_points.min(axis=0)
            y_max, x_max = cluster_points.max(axis=0)
            
            zones.append({
                'x': int(x_min),
                'y': int(y_min),
                'w': int(x_max - x_min),
                'h': int(y_max - y_min)
            })
        
        return zones
    
    def _merge_zone_sets(self, zones1, zones2, w, h):
        """Fusiona dos conjuntos de zonas."""
        # Convertir a formato común
        all_zones = zones1 + zones2
        
        # Ordenar por posición
        all_zones.sort(key=lambda z: (z['y'], z['x']))
        
        return all_zones
    
    def _cleanup_zones(self, zones, w, h):
        """Filtra y limpia zonas."""
        print(f"\n🧹 Fase 4: Limpieza de zonas...")
        
        total_area = w * h
        min_area = total_area * (self.min_zone_area_percent / 100)
        
        # Filtrar por área mínima
        valid_zones = []
        for zone in zones:
            area = zone['w'] * zone['h']
            if area >= min_area:
                valid_zones.append(zone)
        
        # Fusionar zonas superpuestas
        merged_zones = self._merge_overlapping_zones(valid_zones)
        
        return merged_zones
    
    def _merge_overlapping_zones(self, zones):
        """Fusiona zonas que se superponen mucho."""
        if not zones:
            return []
        
        merged = []
        used = set()
        
        for i, z1 in enumerate(zones):
            if i in used:
                continue
            
            current = z1.copy()
            
            for j, z2 in enumerate(zones[i+1:], i+1):
                if j in used:
                    continue
                
                overlap = self._calculate_overlap(current, z2)
                
                if overlap > 0.3:  # 30% overlap
                    # Fusionar
                    x1 = min(current['x'], z2['x'])
                    y1 = min(current['y'], z2['y'])
                    x2 = max(current['x'] + current['w'], z2['x'] + z2['w'])
                    y2 = max(current['y'] + current['h'], z2['y'] + z2['h'])
                    
                    current = {'x': x1, 'y': y1, 'w': x2 - x1, 'h': y2 - y1}
                    used.add(j)
            
            merged.append(current)
            used.add(i)
        
        return merged
    
    def _calculate_overlap(self, z1, z2):
        """Calcula overlap entre dos zonas."""
        x_overlap = max(0, min(z1['x'] + z1['w'], z2['x'] + z2['w']) - max(z1['x'], z2['x']))
        y_overlap = max(0, min(z1['y'] + z1['h'], z2['y'] + z2['h']) - max(z1['y'], z2['y']))
        
        overlap_area = x_overlap * y_overlap
        min_area = min(z1['w'] * z1['h'], z2['w'] * z2['h'])
        
        return overlap_area / min_area if min_area > 0 else 0
    
    def _save_zones(self, img, zones, output_folder, debug):
        """Aplica padding y guarda zonas."""
        print(f"\n💾 Fase 5: Guardando zonas...")
        
        h, w = img.shape[:2]
        final_zones = []
        
        # Ordenar por posición (izq→der, arr→abajo)
        zones.sort(key=lambda z: (z['y'], z['x']))
        
        for i, zone in enumerate(zones, 1):
            # Calcular padding
            pad_h = int(zone['h'] * self.padding_percent / 100)
            pad_w = int(zone['w'] * self.padding_percent / 100)
            
            # Aplicar padding
            x = max(0, zone['x'] - pad_w)
            y = max(0, zone['y'] - pad_h)
            x2 = min(w, zone['x'] + zone['w'] + pad_w)
            y2 = min(h, zone['y'] + zone['h'] + pad_h)
            
            # Recortar
            crop = img[y:y2, x:x2]
            
            # Guardar
            out_path = os.path.join(output_folder, f"zone_{i:02d}.jpg")
            cv2.imwrite(out_path, crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            final_zones.append({
                'id': i,
                'x': x,
                'y': y,
                'width': x2 - x,
                'height': y2 - y,
                'path': out_path
            })
        
        if debug:
            self._create_final_visualization(img, final_zones, output_folder)
        
        return final_zones
    
    def _find_continuous_gaps(self, condition_array, min_gap_size):
        """Encuentra gaps continuos."""
        gaps = []
        in_gap = False
        gap_start = 0
        
        for i, is_gap in enumerate(condition_array):
            if is_gap and not in_gap:
                gap_start = i
                in_gap = True
            elif not is_gap and in_gap:
                if i - gap_start >= min_gap_size:
                    gaps.append((gap_start + i) // 2)
                in_gap = False
        
        return gaps
    
    def _save_projection(self, projection, orientation, threshold, output_folder):
        """Guarda gráfica de proyección."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(14, 5))
            plt.plot(projection, linewidth=2, color='#2E86AB')
            plt.axhline(y=threshold, color='#A23B72', linestyle='--', linewidth=2)
            plt.title(f'Proyección {orientation}', fontsize=12, fontweight='bold')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(output_folder, f"2_projection_{orientation}.png"), dpi=120)
            plt.close()
        except:
            pass
    
    def _visualize_clusters(self, img, pixels, labels, output_folder):
        """Visualiza clusters detectados."""
        debug_img = img.copy()
        
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 0, 0), (0, 128, 0), (0, 0, 128)
        ]
        
        for cluster_id in set(labels):
            if cluster_id == -1:
                continue
            
            color = colors[cluster_id % len(colors)]
            cluster_points = pixels[labels == cluster_id]
            
            for y, x in cluster_points[::10]:  # Cada 10 puntos
                cv2.circle(debug_img, (int(x), int(y)), 2, color, -1)
        
        cv2.imwrite(os.path.join(output_folder, "3_clusters.jpg"), debug_img)
    
    def _create_final_visualization(self, img, zones, output_folder):
        """Visualización final."""
        debug_img = img.copy()
        
        colors = [(255, 50, 50), (50, 255, 50), (50, 50, 255), 
                 (255, 255, 50), (255, 50, 255), (50, 255, 255)]
        
        for zone in zones:
            color = colors[(zone['id'] - 1) % len(colors)]
            x, y = zone['x'], zone['y']
            w, h = zone['width'], zone['height']
            
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), color, 4)
            cv2.putText(debug_img, f"Z{zone['id']}", (x + 15, y + 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 4)
        
        cv2.imwrite(os.path.join(output_folder, "4_final_zones.jpg"), debug_img)

