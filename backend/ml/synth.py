"""Synthetic pill photo renderer.

Real pill datasets (NLM C3PI, ePillID) are large and must be downloaded separately
(see scripts/). To keep the project runnable end to end on a laptop, we render
photo-like pill images from the catalogue's appearance records: shape, colour(s),
imprint, size. Renders vary background, lighting, colour cast, rotation, scale,
blur, noise, shadows and JPEG artefacts so the model learns invariance.

Usage:
    python -m ml.synth --out data/synth --per-class 120
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.config import COLOR_RGB, DATA_DIR

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _font(size: int) -> ImageFont.ImageFont:
    for f in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _jitter(rgb, rng, amount=14):
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255)) for c in rgb)


def _background(size, rng) -> Image.Image:
    kind = rng.choice(["plain", "plain", "gradient", "noise", "cloth", "dark"])
    if kind == "dark":
        base = np.array(_jitter((45, 48, 55), rng, 20), np.float32)
    else:
        base = np.array(_jitter((222, 222, 218), rng, 30), np.float32)
    img = np.ones((size, size, 3), np.float32) * base
    if kind == "gradient":
        g = np.linspace(-25, 25, size, dtype=np.float32)
        img += (g[None, :, None] if rng.random() < 0.5 else g[:, None, None])
    elif kind == "noise":
        img += rng.normal(0, 8, img.shape)
    elif kind == "cloth":
        xs = np.arange(size)
        stripes = 10 * np.sin(xs / rng.uniform(2, 6))
        img += stripes[None, :, None] + stripes[:, None, None] * 0.5
        img += rng.normal(0, 4, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def _shape_polygon(shape: str, w: float, h: float):
    """Return a polygon (list of points) centred at 0,0 for polygonal shapes."""
    if shape == "rectangle":
        r = min(w, h) * 0.18
        pts = []
        for cx, cy, a0 in [(w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)]:
            for t in range(0, 91, 15):
                a = math.radians(a0 + t)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts
    if shape == "diamond":
        return [(0, -h / 2), (w / 2, 0), (0, h / 2), (-w / 2, 0)]
    if shape == "triangle":
        return [(0, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    raise ValueError(shape)


def render_pill(record: dict, rng: np.random.Generator, size: int = 256, clean: bool = False):
    """Render one pill photo. Returns (PIL.Image RGB, PIL.Image L mask)."""
    shape = record["shape"]
    colors = record["colors"]
    scale = 4  # supersample for anti-aliasing
    S = size * scale
    pill_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(pill_layer)

    # Physical size -> pixels. Bigger pills occupy more of the frame.
    base = S * (0.30 + 0.018 * record.get("size_mm", 10)) * (1.0 if clean else rng.uniform(0.8, 1.1))
    base = min(base, S * 0.78)
    aspect = {"round": 1.0, "oval": 0.62, "oblong": 0.45, "capsule": 0.38, "rectangle": 0.55, "diamond": 0.75, "triangle": 0.9}[shape]
    w, h = base, base * aspect
    if shape in ("round", "triangle", "diamond"):
        w = h = base * (0.75 if shape == "round" else 0.8)
        if shape == "diamond":
            h = w * 0.75
    cx, cy = S / 2, S / 2
    c1 = _jitter(COLOR_RGB[colors[0]], rng, 4 if clean else 16)
    c2 = _jitter(COLOR_RGB[colors[1]], rng, 4 if clean else 16) if len(colors) > 1 else c1

    if shape == "capsule":
        r = h / 2
        # left half colour c1, right half c2, rounded ends
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx, cy + h / 2], radius=r, fill=c1 + (255,))
        d.rounded_rectangle([cx - w / 2 + r, cy - h / 2, cx, cy + h / 2], radius=0, fill=c1 + (255,))
        d.rounded_rectangle([cx, cy - h / 2, cx + w / 2, cy + h / 2], radius=r, fill=c2 + (255,))
        d.rectangle([cx, cy - h / 2, cx + w / 2 - r, cy + h / 2], fill=c2 + (255,))
        d.line([cx, cy - h / 2, cx, cy + h / 2], fill=tuple(int(v * 0.8) for v in c2) + (255,), width=scale * 2)
    elif shape in ("round", "oval"):
        d.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=c1 + (255,))
    elif shape == "oblong":
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=h * 0.48, fill=c1 + (255,))
        if len(colors) > 1:  # two-tone caplet
            d.rounded_rectangle([cx, cy - h / 2, cx + w / 2, cy + h / 2], radius=h * 0.48, fill=c2 + (255,))
            d.rectangle([cx, cy - h / 2, cx + w / 4, cy + h / 2], fill=c2 + (255,))
    else:
        pts = [(cx + x, cy + y) for x, y in _shape_polygon(shape, w, h)]
        d.polygon(pts, fill=c1 + (255,))

    # Imprint: debossed look = darker text with a light offset highlight.
    text = record.get("imprint", "")
    if text:
        lines = text.split(" ") if shape in ("round", "diamond", "triangle") and len(text) > 5 else [text]
        tw_max = w * (0.62 if shape != "triangle" else 0.45)
        fs = int(h * (0.36 if len(lines) == 1 else 0.26))
        font = _font(fs)
        while fs > 8 and max(d.textlength(t, font=font) for t in lines) > tw_max:
            fs -= 2
            font = _font(fs)
        dark = tuple(int(v * (0.55 if not clean else 0.5)) for v in c1)
        if sum(c1) < 300:  # dark pill -> light print
            dark = (235, 235, 235)
        light = tuple(min(255, int(v * 1.15) + 10) for v in c1)
        total_h = fs * 1.15 * len(lines)
        y0 = cy - total_h / 2 + (h * 0.12 if shape == "triangle" else 0)
        for i, t in enumerate(lines):
            tw = d.textlength(t, font=font)
            x = cx - tw / 2 - (w * 0.12 if shape in ("capsule",) and len(colors) > 1 and False else 0)
            y = y0 + i * fs * 1.15
            d.text((x + scale, y + scale), t, font=font, fill=light + (255,))
            d.text((x, y), t, font=font, fill=dark + (255,))
    # Score line for some round tablets
    if shape == "round" and record.get("scored"):
        d.line([cx - w / 2, cy, cx + w / 2, cy], fill=tuple(int(v * 0.7) for v in c1) + (255,), width=scale * 2)

    # 3D shading: radial highlight + darker rim
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    lx, ly = (cx - w * 0.2, cy - h * 0.25) if clean else (cx + rng.uniform(-0.35, 0.35) * w, cy + rng.uniform(-0.35, 0.35) * h)
    dist = np.sqrt(((xx - lx) / (w * 0.7)) ** 2 + ((yy - ly) / (h * 0.7 + 1)) ** 2)
    shade = np.clip(1.12 - 0.28 * dist, 0.72, 1.12)
    arr = np.array(pill_layer).astype(np.float32)
    arr[..., :3] *= shade[..., None]
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    pill_layer = Image.fromarray(arr, "RGBA")

    if not clean:  # rotate + translate the pill only (background stays seamless)
        angle = rng.uniform(0, 360)
        tx, ty = (rng.uniform(-0.12, 0.12) * S for _ in range(2))
        pill_layer = pill_layer.rotate(angle, resample=Image.BICUBIC, translate=(tx, ty))
    alpha = pill_layer.split()[-1]

    bg = _background(S, rng) if not clean else Image.new("RGB", (S, S), (228, 228, 226))
    # Soft shadow
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh_alpha = alpha.filter(ImageFilter.GaussianBlur(scale * 6)).point(lambda v: int(v * 0.35))
    shadow.putalpha(sh_alpha)
    off = (int(scale * rng.uniform(2, 10)), int(scale * rng.uniform(2, 10)))
    bg.paste(Image.new("RGB", (S, S), (20, 20, 20)), off, shadow)
    bg.paste(pill_layer, (0, 0), pill_layer)
    mask = alpha

    img = bg.resize((size, size), Image.LANCZOS)
    mask = mask.resize((size, size), Image.LANCZOS)

    if not clean:
        a = np.array(img).astype(np.float32)
        # brightness / contrast / colour cast (warm indoor bulbs, cool daylight)
        a = a * rng.uniform(0.7, 1.2) + rng.uniform(-20, 20)
        a *= np.array([rng.uniform(0.88, 1.12), rng.uniform(0.92, 1.08), rng.uniform(0.85, 1.12)])
        # uneven lighting
        g = np.linspace(rng.uniform(-30, 0), rng.uniform(0, 30), size)
        a += (g[None, :, None] if rng.random() < 0.5 else g[:, None, None])
        a += rng.normal(0, rng.uniform(1, 7), a.shape)
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        if rng.random() < 0.5:
            img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.4)))
    return img, mask


def load_catalogue() -> list[dict]:
    return json.loads((DATA_DIR / "pills.json").read_text())["pills"]


def _render_class(job):
    rec, out, per_class, refs, size, seed = job
    rng = np.random.default_rng(seed)
    rows = []
    n_train, n_val = int(per_class * 0.7), int(per_class * 0.15)
    for split, n in (("train", n_train), ("val", n_val), ("test", per_class - n_train - n_val), ("ref", refs)):
        folder = out / split / rec["pill_id"]
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            img, _ = render_pill(rec, rng, size, clean=(split == "ref" and i == 0))
            p = folder / f"{i:04d}.jpg"
            img.save(p, quality=int(rng.integers(70, 96)))
            rows.append({"path": str(p.relative_to(out)), "split": split, "pill_id": rec["pill_id"], "shape": rec["shape"], "color": rec["colors"][0]})
    return rows


def main():
    from concurrent.futures import ProcessPoolExecutor

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/synth")
    ap.add_argument("--per-class", type=int, default=120)
    ap.add_argument("--refs", type=int, default=6, help="reference images per class for the matching gallery")
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    out = Path(args.out)
    jobs = [(rec, out, args.per_class, args.refs, args.size, args.seed * 1000 + i) for i, rec in enumerate(load_catalogue())]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = [r for chunk in ex.map(_render_class, jobs) for r in chunk]
    (out / "index.json").write_text(json.dumps(rows))
    print(f"wrote {len(rows)} images to {out}")


if __name__ == "__main__":
    main()
