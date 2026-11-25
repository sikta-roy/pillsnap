"""Step 4: pill matching and confidence.

For every candidate pill in the catalogue we compute a fused score:

    logit = w_emb * cosine(photo embedding, nearest reference image of that pill)
          + w_attr * (P(shape of that pill) + P(colour of that pill))
          + w_imp * OCR confidence * imprint_similarity(read text, pill imprint)

and turn the logits into probabilities with a softmax whose temperature was fitted on
held-out data (ml/evaluate.py -> artifacts/calibration.json). Safety rules on top of the
probabilities live in app/safety.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from app.config import CALIBRATION_PATH
from app.pipeline.ocr import imprint_similarity

W_EMB, W_ATTR, W_IMP = 1.0, 0.15, 0.6
DEFAULT_T = 0.05


def load_temperature() -> float:
    try:
        return float(json.loads(CALIBRATION_PATH.read_text())["temperature"])
    except Exception:
        return DEFAULT_T


@dataclass
class Evidence:
    embedding_similarity: float | None
    shape_match: float
    color_match: float
    imprint_similarity: float | None


def score_candidates(
    pills: list[dict],
    shape_probs: dict[str, float],
    color_probs: dict[str, float],
    emb_sims: dict[str, float] | None,
    imprint_text: str,
    imprint_conf: float,
    temperature: float,
) -> list[tuple[dict, float, Evidence]]:
    logits, evs = [], []
    for p in pills:
        e = emb_sims.get(p["pill_id"]) if emb_sims is not None else None
        sp = shape_probs.get(p["shape"], 0.0)
        cp = max(color_probs.get(c, 0.0) for c in p["colors"])
        isim = imprint_similarity(imprint_text, p["imprint"]) if imprint_text else None
        z = W_ATTR * (sp + cp)
        z += W_EMB * (e if e is not None else 0.0)
        if isim is not None:
            z += W_IMP * imprint_conf * isim
        logits.append(z)
        evs.append(Evidence(e, sp, cp, isim))
    z = np.array(logits, np.float64)
    # Without embeddings the logit scale is smaller; widen T accordingly
    T = temperature if emb_sims is not None else max(temperature, 0.08)
    z = (z - z.max()) / T
    p = np.exp(z)
    p /= p.sum()
    order = np.argsort(-p)
    return [(pills[i], float(p[i]), evs[i]) for i in order]
