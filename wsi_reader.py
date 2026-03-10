from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from PIL import Image

try:
    import openslide
except Exception:
    openslide = None


def wsi_supported() -> bool:
    return openslide is not None


def open_wsi(filepath: str):
    if openslide is None:
        raise RuntimeError("OpenSlide is not available in this environment.")
    return openslide.OpenSlide(filepath)


def get_wsi_info(filepath: str) -> Dict[str, object]:
    slide = open_wsi(filepath)
    width, height = slide.dimensions
    return {
        "width": width,
        "height": height,
        "level_count": slide.level_count,
        "properties": dict(slide.properties),
    }


def generate_wsi_thumbnail(filepath: str, output_path: str, size=(800, 800)) -> str:
    slide = open_wsi(filepath)
    thumb = slide.get_thumbnail(size).convert("RGB")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    thumb.save(output_path, format="JPEG", quality=90)
    return output_path


def extract_roi(filepath: str, x: int, y: int, w: int, h: int, level: int = 0) -> Image.Image:
    slide = open_wsi(filepath)
    region = slide.read_region((x, y), level, (w, h)).convert("RGB")
    return region