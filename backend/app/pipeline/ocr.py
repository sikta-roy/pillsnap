"""Step 3: imprint reading (OCR) and imprint matching.

Imprints are stamped (debossed) into the pill, often low contrast and at any
rotation. We estimate the text angle from stroke pixels (morphology), rotate the text
level, then read it at 0 and 180 degrees, each as a contrast-enhanced grey image and as
its inverse, and keep the most confident reading.

Engine: EasyOCR (CRAFT detector + CRNN recogniser, PyTorch). PaddleOCR or TrOCR can
be swapped in by implementing `read(img) -> list[(text, conf)]`.
"""
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from functools import lru_cache

import cv2
import numpy as np

from app.config import OCR_ENABLED, OCR_GPU

log = logging.getLogger(__name__)
ALLOW = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"

# Characters OCR commonly confuses on pills, mapped to one canonical form.
CONFUSIONS = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "|": "1", "S": "5", "B": "8", "Z": "2", "G": "6"})


@lru_cache(maxsize=1)
def _reader():
    if not OCR_ENABLED:
        return None
    try:
        import easyocr

        return easyocr.Reader(["en"], gpu=OCR_GPU, verbose=False)
    except Exception as e:  # model download blocked, package missing, ...
        log.warning("EasyOCR unavailable (%s); imprint OCR disabled", e)
        return None


def ocr_available() -> bool:
    return _reader() is not None


def normalize(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def canonical(text: str) -> str:
    return normalize(text).translate(CONFUSIONS)


def imprint_similarity(read: str, reference: str) -> float:
    """0..1 similarity robust to spacing, case and common OCR confusions."""
    a, b = canonical(read), canonical(reference)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ratio = SequenceMatcher(None, a, b).ratio()
    # partial credit when one fully contains the other (e.g. partial read "650" vs "DOLO650")
    contain = (min(len(a), len(b)) / max(len(a), len(b))) if (a in b or b in a) else 0.0
    return float(max(ratio, 0.5 + 0.5 * contain if contain else 0.0))


def text_angle(gray: np.ndarray, mask: np.ndarray | None) -> float:
    """Estimate imprint orientation: imprint strokes are thin features that differ from
    the pill surface, so black-hat + top-hat morphology isolates them; the minimum-area
    rectangle around those pixels gives the text line angle. Round pills have no
    natural "up", so this matters most for them."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    strokes = cv2.add(cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k), cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k))
    if mask is not None:
        inner = cv2.erode(mask, np.ones((15, 15), np.uint8))
        strokes = cv2.bitwise_and(strokes, strokes, mask=inner)
    _, th = cv2.threshold(strokes, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pts = cv2.findNonZero(th)
    if pts is None or len(pts) < 30:
        return 0.0
    (_, _), (w, h), ang = cv2.minAreaRect(pts)
    if w < h:
        ang += 90
    return float(ang)


def _rotate(img: np.ndarray, ang: float) -> np.ndarray:
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _variants(crop: np.ndarray, mask: np.ndarray | None):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ang = text_angle(gray, mask)
    big = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    eq = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(big)
    up, down = _rotate(eq, ang), _rotate(eq, ang + 180)
    yield from (up, down, 255 - up, 255 - down)


def read_imprint(crop_bgr: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Returns {"text": str, "confidence": float, "engine": str, "candidates": [...]}."""
    reader = _reader()
    if reader is None:
        return {"text": "", "confidence": 0.0, "engine": "unavailable", "candidates": []}
    cands = []
    for vi, img in enumerate(_variants(crop_bgr, mask)):
        if vi == 2 and cands and max(c["confidence"] for c in cands) > 0.85 and max(len(normalize(c["text"])) for c in cands) >= 2:
            break  # both orientations tried and one read well: skip the inverted pass
        try:
            res = reader.readtext(img, allowlist=ALLOW, detail=1, paragraph=False, text_threshold=0.5, low_text=0.3)
        except Exception as e:  # pragma: no cover
            log.warning("OCR failed: %s", e)
            continue
        # order boxes top-to-bottom, left-to-right and join (multi-line imprints)
        res = sorted(res, key=lambda r: (round(np.mean([p[1] for p in r[0]]) / 40), np.mean([p[0] for p in r[0]])))
        words = [(t.strip(), float(c)) for _, t, c in res if normalize(t)]
        if not words:
            continue
        text = " ".join(w for w, _ in words)
        conf = float(np.mean([c for _, c in words]))
        cands.append({"text": text, "confidence": round(conf, 3)})
    if not cands:
        return {"text": "", "confidence": 0.0, "engine": "easyocr", "candidates": []}
    cands.sort(key=lambda c: (-c["confidence"] * min(1.0, len(normalize(c["text"])) / 3)))
    best = cands[0]
    return {"text": best["text"], "confidence": best["confidence"], "engine": "easyocr", "candidates": cands[:4]}
