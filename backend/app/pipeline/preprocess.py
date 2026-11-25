"""Step 1 of the pipeline: image cleanup.

- White balance using the (plain) background as a neutral reference (removes room-light colour casts)
- Pill segmentation: background model from image border + Lab colour distance +
  Otsu threshold + morphology, refined with GrabCut. A learned segmenter (U-Net/SAM)
  can be dropped in via `segment_fn`.
- Crop to the pill, rotate so the long axis is horizontal, neutral background
- CLAHE on the L channel to even out lighting

All functions take/return BGR uint8 numpy arrays (OpenCV convention).
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class Preprocessed:
    crop: np.ndarray            # BGR, background neutralised, upright, square
    crop_raw: np.ndarray        # BGR crop without background removal (for OCR)
    mask: np.ndarray            # uint8 0/255 mask aligned with `crop`
    found: bool                 # was a pill-like object found?
    contour_stats: dict = field(default_factory=dict)
    quality: dict = field(default_factory=dict)


def decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not read the image. Please upload a JPG or PNG photo.")
    return img


def resize_max(img: np.ndarray, max_side: int = 1024) -> np.ndarray:
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    return cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else img


def white_balance(img: np.ndarray) -> np.ndarray:
    """Remove a colour cast using the photo's border as a reference.

    The upload tips ask for a plain (white/grey) background, so when the border is
    close to neutral we treat its tint as the light's colour cast and divide it out.
    Colourful backgrounds are left alone (we cannot tell cast from surface colour).
    Gains are limited to +/-30% so a pill's own colour is never flipped.
    """
    h, w = img.shape[:2]
    b = max(2, int(0.06 * min(h, w)))
    border = np.concatenate([img[:b].reshape(-1, 3), img[-b:].reshape(-1, 3), img[:, :b].reshape(-1, 3), img[:, -b:].reshape(-1, 3)]).astype(np.float32)
    means = border.mean(0) + 1e-6
    chroma = (means.max() - means.min()) / means.mean()
    if chroma > 0.35:  # clearly coloured background
        return img
    gains = np.clip(means.mean() / means, 0.7, 1.3)
    return np.clip(img.astype(np.float32) * gains, 0, 255).astype(np.uint8)


def clahe_l(img: np.ndarray, clip: float = 2.0) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(4, 4)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def image_quality(img: np.ndarray) -> dict:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    bright = float(gray.mean())
    issues = []
    if sharp < 25:
        issues.append("blurry")
    if bright < 50:
        issues.append("too_dark")
    if bright > 225:
        issues.append("too_bright")
    return {"sharpness": round(sharp, 1), "brightness": round(bright, 1), "issues": issues}


def _border_background_distance(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    b = max(2, int(0.06 * min(h, w)))
    border = np.concatenate([lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3), lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3)])
    # Background may have a gradient: fit a plane per channel over the border pixels.
    ys, xs = np.mgrid[0:h, 0:w]
    bm = np.zeros((h, w), bool)
    bm[:b] = bm[-b:] = True
    bm[:, :b] = bm[:, -b:] = True
    A = np.stack([xs[bm], ys[bm], np.ones(bm.sum())], 1).astype(np.float32)
    full = np.stack([xs.ravel(), ys.ravel(), np.ones(h * w)], 1).astype(np.float32)
    dist = np.zeros((h, w), np.float32)
    weights = np.array([0.6, 1.4, 1.4], np.float32)  # chroma matters more than lightness (shadows)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, lab[..., c][bm], rcond=None)
        bg_c = (full @ coef).reshape(h, w)
        dist += weights[c] * (lab[..., c] - bg_c) ** 2
    _ = border  # kept for readability
    return np.sqrt(dist)


def segment_pill(img: np.ndarray) -> tuple[np.ndarray, bool]:
    """Return (mask 0/255, found)."""
    h, w = img.shape[:2]
    dist = _border_background_distance(img)
    d8 = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, th = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k, iterations=2)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, k, iterations=1)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return np.zeros((h, w), np.uint8), False
    # prefer large contours near the centre
    def score(c):
        area = cv2.contourArea(c)
        x, y, cw, ch = cv2.boundingRect(c)
        cxd = abs(x + cw / 2 - w / 2) / w + abs(y + ch / 2 - h / 2) / h
        return area * (1.0 - 0.8 * cxd)
    best = max(cnts, key=score)
    area_frac = cv2.contourArea(best) / (h * w)
    if area_frac < 0.003 or area_frac > 0.92:
        return np.zeros((h, w), np.uint8), False
    mask = np.zeros((h, w), np.uint8)
    cv2.drawContours(mask, [best], -1, 255, -1)

    # GrabCut refinement seeded from the coarse mask
    try:
        gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
        gc[cv2.erode(mask, k, iterations=3) > 0] = cv2.GC_FGD
        gc[cv2.dilate(mask, k, iterations=2) > 0] = np.where(gc[cv2.dilate(mask, k, iterations=2) > 0] == cv2.GC_FGD, cv2.GC_FGD, cv2.GC_PR_FGD)
        gc[cv2.dilate(mask, k, iterations=6) == 0] = cv2.GC_BGD
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(img, gc, None, bgd, fgd, 2, cv2.GC_INIT_WITH_MASK)
        refined = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        cnts2, _ = cv2.findContours(refined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts2:
            c2 = max(cnts2, key=cv2.contourArea)
            ratio = cv2.contourArea(c2) / max(1, cv2.contourArea(best))
            if 0.6 < ratio < 1.4:
                mask = np.zeros((h, w), np.uint8)
                cv2.drawContours(mask, [c2], -1, 255, -1)
    except cv2.error:
        pass
    return mask, True


def contour_stats(mask: np.ndarray) -> dict:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return {}
    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    hull = cv2.convexHull(c)
    peri = cv2.arcLength(hull, True)  # hull perimeter: robust to jagged pixel edges
    (_, _), (rw, rh), _ = cv2.minAreaRect(c)
    approx = cv2.approxPolyDP(c, 0.035 * peri, True)
    return {
        "circularity": float(4 * np.pi * area / (peri ** 2 + 1e-6)),
        "aspect_ratio": float(min(rw, rh) / (max(rw, rh) + 1e-6)),
        "solidity": float(area / (cv2.contourArea(hull) + 1e-6)),
        "extent": float(area / (rw * rh + 1e-6)),
        "vertices": int(len(approx)),
    }


def _upright_crop(img: np.ndarray, mask: np.ndarray, pad: float = 0.12) -> tuple[np.ndarray, np.ndarray]:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    (cx, cy), (rw, rh), ang = cv2.minAreaRect(c)
    if rw < rh:
        ang += 90
    M = cv2.getRotationMatrix2D((cx, cy), ang, 1.0)
    h, w = img.shape[:2]
    rot = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    rmask = cv2.warpAffine(mask, M, (w, h), flags=cv2.INTER_NEAREST)
    side = int(max(rw, rh) * (1 + 2 * pad))
    x0, y0 = int(cx - side / 2), int(cy - side / 2)
    # pad to allow crops beyond the border
    P = side
    rot = cv2.copyMakeBorder(rot, P, P, P, P, cv2.BORDER_REPLICATE)
    rmask = cv2.copyMakeBorder(rmask, P, P, P, P, cv2.BORDER_CONSTANT, value=0)
    return rot[y0 + P:y0 + P + side, x0 + P:x0 + P + side], rmask[y0 + P:y0 + P + side, x0 + P:x0 + P + side]


def preprocess(img: np.ndarray, out_size: int = 256, segment_fn=None) -> Preprocessed:
    img = resize_max(img)
    quality = image_quality(img)
    wb = white_balance(img)
    mask, found = (segment_fn or segment_pill)(wb)
    if not found:
        # fall back to a centre crop so the rest of the pipeline can still run
        h, w = wb.shape[:2]
        s = int(min(h, w) * 0.8)
        y0, x0 = (h - s) // 2, (w - s) // 2
        raw = wb[y0:y0 + s, x0:x0 + s]
        m = np.full(raw.shape[:2], 255, np.uint8)
    else:
        raw, m = _upright_crop(wb, mask)
    raw = cv2.resize(raw, (out_size, out_size), interpolation=cv2.INTER_AREA)
    m = cv2.resize(m, (out_size, out_size), interpolation=cv2.INTER_NEAREST)
    lit = clahe_l(raw)
    neutral = np.full_like(lit, 128)
    soft = cv2.GaussianBlur(m, (5, 5), 0).astype(np.float32)[..., None] / 255.0
    crop = (lit * soft + neutral * (1 - soft)).astype(np.uint8)
    return Preprocessed(crop=crop, crop_raw=lit, mask=m, found=found, contour_stats=contour_stats(m) if found else {}, quality=quality)


def to_data_url(img: np.ndarray, quality: int = 85) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
