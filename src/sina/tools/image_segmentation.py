import io
import os
import base64
import numpy as np
from PIL import Image
from io import BytesIO
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
import matplotlib.patches as patches
from sklearn.cluster import MiniBatchKMeans
from sklearn.cluster import AgglomerativeClustering
from scipy.cluster.hierarchy import dendrogram, linkage

def load_image(path: Path):
    Image.MAX_IMAGE_PIXELS = None
    image = Image.open(path)
    return image

def image_segmentator(
        image: Image.Image, 
        eps: int, 
        min_samples: int, 
        threshold: int = 240,
        downsample_factor: int = 8):  # Factor 8 para folletos grandes
    
    # Calcular nuevo tamaño
    new_width = image.width // downsample_factor
    new_height = image.height // downsample_factor
    
    print(f"Imagen original: {image.width}x{image.height}")
    print(f"Imagen reducida: {new_width}x{new_height}")
    
    # Reducir imagen para el análisis
    small_image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )
    
    gray = np.array(small_image.convert('L'))
    mask_content = gray < threshold

    coords = np.column_stack(np.where(mask_content))
    
    print(f"Píxeles de contenido: {len(coords):,}")
    
    # Limitar aún más si sigue siendo mucho
    if len(coords) > 50000:
        sample_size = 50000
        indices = np.random.choice(len(coords), sample_size, replace=False)
        coords = coords[indices]
        print(f"Muestreado a: {len(coords):,} píxeles")

    dbscan = DBSCAN(
        eps=eps,  # Ya no dividas el eps, usa el valor directo
        min_samples=min_samples,
        n_jobs=-1  # Usar todos los cores
    )

    print("Ejecutando DBSCAN...")
    labels = dbscan.fit_predict(coords)
    print(f"Clusters encontrados: {len(set(labels)) - (1 if -1 in labels else 0)}")
    
    bboxes = []

    for cluster_id in set(labels):
        if cluster_id == -1:
            continue
        
        cluster_coords = coords[labels == cluster_id]
        
        y_min, x_min = cluster_coords.min(axis=0)
        y_max, x_max = cluster_coords.max(axis=0)
        
        # Escalar de vuelta a coordenadas originales
        padding = 20  # Un poco más de padding
        x_min = max(0, (x_min * downsample_factor) - padding)
        y_min = max(0, (y_min * downsample_factor) - padding)
        x_max = min(image.width, (x_max * downsample_factor) + padding)
        y_max = min(image.height, (y_max * downsample_factor) + padding)
        
        bboxes.append({
            'bbox': (int(x_min), int(y_min), int(x_max), int(y_max)),
            'cluster_id': cluster_id,
            'num_pixels': len(cluster_coords)
        })

    # Ordenar por posición vertical (top to bottom)
    bboxes.sort(key=lambda b: b['bbox'][1])
    
    return bboxes

def image_segmentator_hierarchical(
        image: Image.Image, 
        n_clusters: int = None,  # Si None, usa distance_threshold
        distance_threshold: float = None,  # Distancia máxima para fusionar
        threshold: int = 240,
        downsample_factor: int = 8,
        linkage_method: str = 'ward'):  # 'ward', 'complete', 'average', 'single'
    
    new_width = image.width // downsample_factor
    new_height = image.height // downsample_factor
    
    print(f"Imagen original: {image.width}x{image.height}")
    print(f"Imagen reducida: {new_width}x{new_height}")
    
    small_image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )
    
    gray = np.array(small_image.convert('L'))
    mask_content = gray < threshold
    coords = np.column_stack(np.where(mask_content))
    
    print(f"Píxeles de contenido: {len(coords):,}")
    
    # Muestreo si hay muchos píxeles
    if len(coords) > 50000:
        sample_size = 50000
        indices = np.random.choice(len(coords), sample_size, replace=False)
        coords = coords[indices]
        print(f"Muestreado a: {len(coords):,} píxeles")
    
    # Configurar clustering jerárquico
    # Si especificas n_clusters, no uses distance_threshold y viceversa
    if n_clusters is not None:
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage=linkage_method
        )
    else:
        # Auto-detectar número de clusters basado en distancia
        if distance_threshold is None:
            distance_threshold = 100  # Valor por defecto
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            linkage=linkage_method
        )
    
    print("Ejecutando Clustering Jerárquico...")
    labels = clustering.fit_predict(coords)
    print(f"Clusters encontrados: {len(set(labels))}")
    
    bboxes = []
    
    for cluster_id in set(labels):
        cluster_coords = coords[labels == cluster_id]
        
        y_min, x_min = cluster_coords.min(axis=0)
        y_max, x_max = cluster_coords.max(axis=0)
        
        # Escalar de vuelta a coordenadas originales
        padding = 20
        x_min = max(0, (x_min * downsample_factor) - padding)
        y_min = max(0, (y_min * downsample_factor) - padding)
        x_max = min(image.width, (x_max * downsample_factor) + padding)
        y_max = min(image.height, (y_max * downsample_factor) + padding)
        
        bboxes.append({
            'bbox': (int(x_min), int(y_min), int(x_max), int(y_max)),
            'cluster_id': int(cluster_id),
            'num_pixels': len(cluster_coords)
        })
    
    bboxes.sort(key=lambda b: b['bbox'][1])
    
    return bboxes

def image_segmentator_kmeans(
        image: Image.Image, 
        n_clusters: int = 10,  # Número de secciones esperadas
        threshold: int = 240,
        downsample_factor: int = 8,
        merge_nearby: bool = True,  # Fusionar clusters cercanos
        merge_distance: float = 100):  # Distancia para fusionar
    
    new_width = image.width // downsample_factor
    new_height = image.height // downsample_factor
    
    print(f"Imagen original: {image.width}x{image.height}")
    print(f"Imagen reducida: {new_width}x{new_height}")
    
    small_image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )
    
    gray = np.array(small_image.convert('L'))
    mask_content = gray < threshold
    coords = np.column_stack(np.where(mask_content))
    
    print(f"Píxeles de contenido: {len(coords):,}")
    
    # MiniBatchKMeans es más eficiente para grandes datasets
    if len(coords) > 100000:
        print("Usando MiniBatchKMeans (más rápido)...")
        kmeans = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=42,
            batch_size=1000,
            n_init=3
        )
    else:
        from sklearn.cluster import KMeans
        print("Usando KMeans estándar...")
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10
        )
    
    print("Ejecutando K-Means...")
    labels = kmeans.fit_predict(coords)
    print(f"Clusters creados: {n_clusters}")
    
    bboxes = []
    
    for cluster_id in range(n_clusters):
        cluster_coords = coords[labels == cluster_id]
        
        if len(cluster_coords) == 0:
            continue
        
        y_min, x_min = cluster_coords.min(axis=0)
        y_max, x_max = cluster_coords.max(axis=0)
        
        # Escalar de vuelta a coordenadas originales
        padding = 20
        x_min = max(0, (x_min * downsample_factor) - padding)
        y_min = max(0, (y_min * downsample_factor) - padding)
        x_max = min(image.width, (x_max * downsample_factor) + padding)
        y_max = min(image.height, (y_max * downsample_factor) + padding)
        
        bboxes.append({
            'bbox': (int(x_min), int(y_min), int(x_max), int(y_max)),
            'cluster_id': int(cluster_id),
            'num_pixels': len(cluster_coords),
            'center': (int((x_min + x_max) / 2), int((y_min + y_max) / 2))
        })
    
    # Opcional: fusionar bboxes que estén muy cerca
    if merge_nearby:
        bboxes = merge_close_bboxes(bboxes, merge_distance)
    
    bboxes.sort(key=lambda b: b['bbox'][1])
    
    return bboxes

def merge_close_bboxes(bboxes: list, max_distance: float) -> list:
    """Fusiona bounding boxes que estén cerca uno del otro"""
    if len(bboxes) <= 1:
        return bboxes
    
    merged = []
    used = set()
    
    for i, bbox1 in enumerate(bboxes):
        if i in used:
            continue
        
        current_group = [bbox1]
        x1_min, y1_min, x1_max, y1_max = bbox1['bbox']
        
        for j, bbox2 in enumerate(bboxes[i+1:], start=i+1):
            if j in used:
                continue
            
            x2_min, y2_min, x2_max, y2_max = bbox2['bbox']
            
            # Calcular distancia entre centros
            center1 = ((x1_min + x1_max) / 2, (y1_min + y1_max) / 2)
            center2 = ((x2_min + x2_max) / 2, (y2_min + y2_max) / 2)
            distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
            
            if distance < max_distance:
                current_group.append(bbox2)
                used.add(j)
        
        # Crear bbox combinado
        all_x_min = min(b['bbox'][0] for b in current_group)
        all_y_min = min(b['bbox'][1] for b in current_group)
        all_x_max = max(b['bbox'][2] for b in current_group)
        all_y_max = max(b['bbox'][3] for b in current_group)
        
        merged.append({
            'bbox': (all_x_min, all_y_min, all_x_max, all_y_max),
            'cluster_id': len(merged),
            'num_pixels': sum(b['num_pixels'] for b in current_group)
        })
        
        used.add(i)
    
    return merged

def visualizer(image: Image.Image, bboxes: list):
    fig, ax = plt.subplots(1, figsize=(12,16))
    ax.imshow(image)

    colors = plt.cm.tab20(np.linspace(0, 1, len(bboxes)))

    for i, bbox_info in enumerate(bboxes):
        x1, y1, x2, y2, = bbox_info['bbox']
        width = x2 - x1
        height = y2 - y1

        rect = patches.Rectangle(
            (x1, y1), width, height,
            linewidth = 2,
            edgecolor = colors[i],
            facecolor = 'none'
        )
        ax.add_patch(rect)

        ax.text(
            x1, y1 - 5,
            f"Sección {i+1}",
            color = colors[i],
            fontsize = 10,
            fontweight = 'bold',
            bbox = dict(boxstyle = 'round, pad=0.3', facecolor='white', alpha=0.7)
        )

    ax.axis('off')
    plt.tight_layout()
    plt.show()

def image_cropper(
        image: Image.Image, 
        bboxes: list, 
        output_dir: Path):
    
    for i, bbox_info in enumerate(bboxes):
        x1, y1, x2, y2 = bbox_info['bbox']

        cut = image.crop((x1, y1, x2, y2))

        output_path = os.path.join(output_dir, f"{i}.png")
        cut.save(output_path)