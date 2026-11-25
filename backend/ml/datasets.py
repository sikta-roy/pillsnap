"""Datasets, preprocessing cache and the P x K batch sampler used for triplet training.

All sources are normalised to one manifest format (list of dicts):
    {"path": <relative image path>, "split": train|val|test|ref,
     "pill_id": <class id>, "shape": <SHAPES item>, "color": <COLORS item>}

- Synthetic renders: written by ml/synth.py (index.json)
- NLM C3PI: scripts/download_c3pi.py writes manifest.json in the same format
- ePillID: scripts/prepare_epillid.py converts the official CSVs
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, Sampler

from app.config import COLORS, SHAPES
from app.pipeline.preprocess import preprocess

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def load_manifest(root: Path) -> list[dict]:
    for name in ("index.json", "manifest.json"):
        p = root / name
        if p.exists():
            return json.loads(p.read_text())
    raise FileNotFoundError(f"No index.json/manifest.json in {root}")


def _prep_one(args):
    src, dst, size = args
    if Path(dst).exists():
        return
    img = cv2.imread(src)
    if img is None:
        return
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(dst, preprocess(img, out_size=size).crop, [cv2.IMWRITE_JPEG_QUALITY, 92])


def build_cache(root: Path, rows: list[dict], size: int, workers: int = 4) -> Path:
    """Run the same cleanup step the API uses (segment, crop, upright, CLAHE) once per image."""
    cache = root / f"_cache_{size}"
    jobs = [(str(root / r["path"]), str(cache / r["path"]), size) for r in rows if not (cache / r["path"]).exists()]
    if jobs:
        print(f"preprocessing {len(jobs)} images -> {cache}")
        with ProcessPoolExecutor(workers) as ex:
            list(ex.map(_prep_one, jobs, chunksize=16))
    return cache


def to_tensor(bgr: np.ndarray, size: int) -> torch.Tensor:
    rgb = cv2.cvtColor(cv2.resize(bgr, (size, size), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return torch.from_numpy(((rgb - MEAN) / STD).transpose(2, 0, 1).copy())


def augment(bgr: np.ndarray, rng: random.Random) -> np.ndarray:
    """Geometry + mild photometric noise. No hue shifts and no mirror flips:
    colour is a label and mirrored imprints do not exist in reality."""
    h, w = bgr.shape[:2]
    ang = rng.choice([0, 180]) + rng.uniform(-12, 12)
    sc = rng.uniform(0.88, 1.08)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, sc)
    M[:, 2] += [rng.uniform(-0.05, 0.05) * w, rng.uniform(-0.05, 0.05) * h]
    out = cv2.warpAffine(bgr, M, (w, h), borderValue=(128, 128, 128)).astype(np.float32)
    out = out * rng.uniform(0.85, 1.15) + rng.uniform(-12, 12)
    if rng.random() < 0.3:
        out = cv2.GaussianBlur(out, (3, 3), 0)
    return np.clip(out, 0, 255).astype(np.uint8)


class PillDataset(Dataset):
    def __init__(self, root: Path, rows: list[dict], classes: list[str], size: int, train: bool, cache_size: int = 160):
        self.root = Path(root)
        self.cache = build_cache(self.root, rows, cache_size)
        self.rows = [r for r in rows if (self.cache / r["path"]).exists()]
        self.cls = {c: i for i, c in enumerate(classes)}
        self.size, self.train = size, train
        self.rng = random.Random(0)
        self.labels = [self.cls[r["pill_id"]] for r in self.rows]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        img = cv2.imread(str(self.cache / r["path"]))
        if self.train:
            img = augment(img, self.rng)
        # ePillID has no shape/colour labels: -100 is ignored by the cross-entropy loss
        shape = SHAPES.index(r["shape"]) if r.get("shape") in SHAPES else -100
        color = COLORS.index(r["color"]) if r.get("color") in COLORS else -100
        return to_tensor(img, self.size), self.labels[i], shape, color


class PKSampler(Sampler):
    """Yields batches with P classes x K images each (needed for batch-hard mining)."""

    def __init__(self, labels: list[int], p: int, k: int, seed: int = 0):
        self.by_cls = defaultdict(list)
        for i, l in enumerate(labels):
            self.by_cls[l].append(i)
        self.p, self.k = min(p, len(self.by_cls)), k
        self.rng = random.Random(seed)
        self.n_batches = max(1, len(labels) // (self.p * self.k))

    def __iter__(self):
        classes = list(self.by_cls)
        for _ in range(self.n_batches):
            batch = []
            for c in self.rng.sample(classes, self.p):
                idx = self.by_cls[c]
                batch += self.rng.sample(idx, self.k) if len(idx) >= self.k else self.rng.choices(idx, k=self.k)
            yield batch

    def __len__(self):
        return self.n_batches
