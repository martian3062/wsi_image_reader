from typing import Dict


def feature_vector_from_analysis(row) -> Dict[str, float]:
    return {
        "avg_intensity": float(row["avg_intensity"] or 0),
        "intensity_std": float(row["intensity_std"] or 0),
        "edge_density": float(row["edge_density"] or 0),
        "redness_score": float(row["redness_score"] or 0),
        "saturation_score": float(row["saturation_score"] or 0),
        "tissue_ratio": float(row["tissue_ratio"] or 0),
        "risk_score": float(row["risk_score"] or 0),
    }


def simple_pattern_flags(features: Dict[str, float]) -> Dict[str, bool]:
    return {
        "high_texture": features["edge_density"] > 0.08,
        "high_redness": features["redness_score"] > 0.08,
        "high_variation": features["intensity_std"] > 40,
        "dense_tissue": features["tissue_ratio"] > 0.70,
    }