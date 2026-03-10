from typing import Dict


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def compute_risk(features: Dict[str, float]) -> Dict[str, object]:
    norm_std = clamp(features.get("intensity_std", 0.0) / 90.0)
    norm_edges = clamp(features.get("edge_density", 0.0) / 0.20)
    norm_red = clamp(features.get("redness_score", 0.0) / 0.30)
    norm_sat = clamp(features.get("saturation_score", 0.0) / 0.70)
    norm_tissue = clamp(features.get("tissue_ratio", 0.0))

    risk_score_0_1 = (
        0.22 * norm_std
        + 0.20 * norm_edges
        + 0.22 * norm_red
        + 0.18 * norm_sat
        + 0.18 * norm_tissue
    )
    risk_score = round(risk_score_0_1 * 100.0, 2)

    if risk_score < 25:
        pattern_label = "Low visual abnormality pattern"
    elif risk_score < 50:
        pattern_label = "Mild irregular pattern"
    elif risk_score < 75:
        pattern_label = "Moderate irregular pattern"
    else:
        pattern_label = "High irregular pattern"

    reasons = []
    if norm_red > 0.6:
        reasons.append("higher red-channel prominence")
    if norm_edges > 0.6:
        reasons.append("dense edge/texture activity")
    if norm_std > 0.6:
        reasons.append("strong grayscale variation")
    if norm_tissue > 0.7:
        reasons.append("high tissue-like coverage")
    if norm_sat > 0.6:
        reasons.append("high color saturation")

    if reasons:
        summary = "This heuristic score is driven mainly by " + ", ".join(reasons[:3]) + "."
    else:
        summary = "This image shows relatively low visual irregularity by the current heuristic."

    return {
        "risk_score": risk_score,
        "pattern_label": pattern_label,
        "summary": summary,
    }