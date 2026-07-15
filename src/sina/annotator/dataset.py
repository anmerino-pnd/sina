"""
Consolidador del dataset YOLO de zonas de flyers.

Cada vez que el humano guarda anotaciones en el anotador, `process_annotations`
exporta las cajas corregidas a `datos/flyers/<tienda>/<ciudad>/<fecha>/labels_yolo/`.
Esos .txt dispersos no son entrenables por sí solos: este módulo los barre, los
empareja con su imagen fuente y arma la estructura estándar de Ultralytics en
`datos/yolo_dataset/` (images/labels × train/val + data.yaml), lista para:

    yolo detect train data=datos/yolo_dataset/data.yaml model=yolo11n.pt imgsz=1024

Decisiones (documentadas en quarto/7_estado.qmd):
  - Modelo UNIFICADO: un solo dataset con todas las tiendas (la diversidad de
    layouts generaliza mejor que un modelo por tienda con pocos datos).
  - Split determinista por hash del nombre → reproducible entre corridas; una
    página nunca cambia de split al re-ejecutar, aunque lleguen datos nuevos.
  - Nombres `tienda__ciudad__fecha__page_NN` → sin colisiones y trazables al flyer.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from sina.config.paths import DATA, FLYERS_DATA

# Extensiones aceptadas como imagen fuente del label (el anotador guarda .jpg).
_EXTS_IMAGEN = (".jpg", ".jpeg", ".png")


def _split_de(nombre: str, val_frac: float) -> str:
    """train/val determinista: hash del nombre → estable entre corridas."""
    h = int(hashlib.md5(nombre.encode("utf-8")).hexdigest(), 16)
    return "val" if (h % 1000) < int(val_frac * 1000) else "train"


def _imagen_para(label_path: Path) -> Path | None:
    """La imagen fuente vive en la carpeta de la fecha (padre de labels_yolo/)."""
    carpeta_fecha = label_path.parent.parent
    for ext in _EXTS_IMAGEN:
        candidata = carpeta_fecha / f"{label_path.stem}{ext}"
        if candidata.exists():
            return candidata
    return None


def construir_dataset_yolo(
    destino: Path | None = None, val_frac: float = 0.1
) -> dict:
    """
    Reconstruye `datos/yolo_dataset/` desde cero con todos los labels_yolo
    acumulados bajo `datos/flyers/`. Idempotente: misma entrada → mismo dataset.
    Devuelve un resumen {train, val, tiendas, huerfanos}.
    """
    destino = destino or (DATA / "yolo_dataset")
    if destino.exists():
        shutil.rmtree(destino)
    for split in ("train", "val"):
        (destino / "images" / split).mkdir(parents=True, exist_ok=True)
        (destino / "labels" / split).mkdir(parents=True, exist_ok=True)

    resumen: dict = {"train": 0, "val": 0, "tiendas": {}, "huerfanos": 0}

    for label in sorted(FLYERS_DATA.glob("*/*/*/labels_yolo/*.txt")):
        imagen = _imagen_para(label)
        if imagen is None:
            print(f"[!] Sin imagen para {label} — se omite.")
            resumen["huerfanos"] += 1
            continue

        # <tienda>/<ciudad>/<fecha>/labels_yolo/<stem>.txt
        fecha = label.parent.parent.name
        ciudad = label.parent.parent.parent.name
        tienda = label.parent.parent.parent.parent.name
        nombre = f"{tienda}__{ciudad}__{fecha}__{label.stem}"
        split = _split_de(nombre, val_frac)

        shutil.copy2(imagen, destino / "images" / split / f"{nombre}{imagen.suffix}")
        shutil.copy2(label, destino / "labels" / split / f"{nombre}.txt")
        resumen[split] += 1
        resumen["tiendas"][tienda] = resumen["tiendas"].get(tienda, 0) + 1

    # data.yaml con rutas relativas al propio dataset (portable).
    (destino / "data.yaml").write_text(
        "\n".join(
            [
                f"path: {destino.resolve().as_posix()}",
                "train: images/train",
                "val: images/val",
                "nc: 1",
                "names: [zona]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return resumen


if __name__ == "__main__":
    print(json.dumps(construir_dataset_yolo(), ensure_ascii=False, indent=2))
