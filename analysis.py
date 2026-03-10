from __future__ import annotations

from typing import Dict, Any

import cv2
import numpy as np
from PIL import Image

from risk_engine import compute_risk

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svs"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_pil_image(img: Image.Image) -> Dict[str, Any]:
    width, height = img.size

    img_small = img.copy().convert("RGB")
    img_small.thumbnail((512, 512))

    rgb = np.array(img_small).astype(np.uint8)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    avg_intensity = float(np.mean(gray))
    intensity_std = float(np.std(gray))

    edges = cv2.Canny(gray, 80, 160)
    edge_density = float(np.mean(edges > 0))

    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)

    redness_raw = r - ((g + b) / 2.0)
    redness_score = float(np.mean(np.clip(redness_raw, 0, None)) / 255.0)
    saturation_score = float(np.mean(hsv[:, :, 1]) / 255.0)

    tissue_mask = gray < 235
    tissue_ratio = float(np.mean(tissue_mask))

    features = {
        "width": width,
        "height": height,
        "avg_intensity": round(avg_intensity, 3),
        "intensity_std": round(intensity_std, 3),
        "edge_density": round(edge_density, 5),
        "redness_score": round(redness_score, 5),
        "saturation_score": round(saturation_score, 5),
        "tissue_ratio": round(tissue_ratio, 5),
    }

    features.update(compute_risk(features))
    return features


def analyze_image(image_path: str) -> Dict[str, Any]:
    img = Image.open(image_path).convert("RGB")
    return analyze_pil_image(img)