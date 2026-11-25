"""Step 2: feature detection.

Two independent detectors whose outputs are fused:
1. PillNet (deep learning): embedding + shape + colour heads (ml/models.py)
2. Classical vision: contour geometry for shape, k-means in Lab for colour

The classical detectors keep the app working when no trained model is present and
act as a sanity check on the CNN when photos look unlike its training data.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.config import COLOR_RGB, COLORS, SHAPES


def _named_color_lab():
    rgb = np.array([COLOR_RGB[c] for c in COLORS], np.uint8)[None]
    return cv2.cvtColor(rgb[..., ::-1], cv2.COLOR_BGR2LAB)[0].astype(np.float32)


_NAMED_LAB = _named_color_lab()


def classical_colors(crop_bgr: np.ndarray, mask: np.ndarray, k: int = 3) -> dict[str, float]:
    """Distribution over COLORS from k-means on pill pixels (imprint pixels are a minority cluster)."""
    pix = crop_bgr[cv2.erode(mask, np.ones((7, 7), np.uint8)) > 0]
    if len(pix) < 50:
        return {c: 1 / len(COLORS) for c in COLORS}
    lab = cv2.cvtColor(pix[None].astype(np.uint8), cv2.COLOR_BGR2LAB)[0].astype(np.float32)
    k = min(k, len(lab))
    _, lbl, centers = cv2.kmeans(lab, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 2, cv2.KMEANS_PP_CENTERS)
    weights = np.bincount(lbl.ravel(), minlength=k) / len(lbl)
    scores = np.zeros(len(COLORS), np.float32)
    for c, w in zip(centers, weights):
        d = np.linalg.norm((_NAMED_LAB - c) * np.array([0.5, 1.0, 1.0]), axis=1)
        p = np.exp(-d / 12.0)
        scores += w * p / (p.sum() + 1e-6)
    scores /= scores.sum() + 1e-6
    return {c: float(s) for c, s in zip(COLORS, scores)}


def classical_shape(stats: dict, two_tone: bool = False) -> dict[str, float]:
    """Rule-based shape probabilities from contour geometry."""
    if not stats:
        return {s: 1 / len(SHAPES) for s in SHAPES}
    ar, circ, ext, v = stats["aspect_ratio"], stats["circularity"], stats["extent"], stats["vertices"]
    s = {x: 0.02 for x in SHAPES}
    if ext < 0.62 and v <= 4:
        s["triangle" if ext < 0.56 else "diamond"] += 1.0
    elif ar > 0.85:
        s["round"] += 1.0 if circ > 0.8 else 0.6
        s["rectangle"] += 0.3 if ext > 0.88 else 0.0
    elif ar > 0.55:
        if ext > 0.88:
            s["rectangle"] += 1.0
        else:
            s["oval"] += 1.0
    else:
        if two_tone:
            s["capsule"] += 1.0
        else:
            s["oblong"] += 0.8
            s["capsule"] += 0.3
        if ext > 0.93:
            s["rectangle"] += 0.3
    tot = sum(s.values())
    return {k: v / tot for k, v in s.items()}


def fuse(cnn: dict[str, float] | None, classical: dict[str, float], w_cnn: float = 0.6) -> dict[str, float]:
    if cnn is None:
        return classical
    out = {k: w_cnn * cnn.get(k, 0) + (1 - w_cnn) * classical.get(k, 0) for k in classical}
    tot = sum(out.values()) + 1e-9
    return {k: v / tot for k, v in out.items()}


def top(d: dict[str, float], n: int = 3) -> list[dict]:
    return [{"label": k, "confidence": round(v, 3)} for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n]]


def is_two_tone(color_dist: dict[str, float]) -> bool:
    vals = sorted(color_dist.values(), reverse=True)
    return len(vals) > 1 and vals[1] > 0.3
