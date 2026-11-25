"""Download NLM C3PI / Pillbox reference pill images and build a training manifest.

The NLM Computational Photography Project for Pill Identification (C3PI) published
~130k pill photos with NDC codes, plus the (retired, archived) Pillbox attribute table
with shape, colour, imprint, size, strength and manufacturer for each product.

    python scripts/download_c3pi.py --pillbox-csv path/to/pillbox.csv --out data/c3pi --max-classes 2000

Steps
1. Read the Pillbox CSV (download the archived "pillbox" full data CSV from the NLM
   data portal; set --pillbox-csv). Columns used are listed in COLS below.
2. Download each product's images from the C3PI image server (--image-base).
3. Write data/c3pi/manifest.json (same format as ml/synth.py) and
   data/c3pi/catalog_pills.json (records for app/data/pills.json).

Splits: per product, the studio reference image(s) -> "ref"; the rest -> train/val/test.

NOTE: host names and column names have changed over the years. Check the current NLM
data portal (https://data.lhncbc.nlm.nih.gov/public/Pills/) and adjust --image-base and
COLS if needed. This script was not run in the build environment (no network access).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import COLORS, SHAPES  # noqa: E402

COLS = {
    "id": ["product_code", "ndc9", "setid_product", "id"],
    "name": ["medicine_name", "rxstring", "title"],
    "strength": ["spl_strength", "strength"],
    "maker": ["author", "manufacturer", "labeler"],
    "shape": ["splshape_text", "shape"],
    "color": ["splcolor_text", "color"],
    "imprint": ["splimprint", "imprint"],
    "size": ["splsize", "size"],
    "image": ["image_id", "image_filename", "file_name"],
}
SHAPE_MAP = {"ROUND": "round", "OVAL": "oval", "CAPSULE": "oblong", "RECTANGLE": "rectangle", "DIAMOND": "diamond", "TRIANGLE": "triangle", "BULLET": "oblong", "TEAR": "oval"}
COLOR_MAP = {"WHITE": "white", "YELLOW": "yellow", "ORANGE": "orange", "PINK": "pink", "RED": "red", "BROWN": "brown", "GREEN": "green", "BLUE": "blue", "PURPLE": "purple", "TURQUOISE": "blue", "GRAY": "white", "BLACK": "brown"}


def col(row: dict, key: str) -> str:
    for c in COLS[key]:
        if c in row and row[c]:
            return row[c].strip()
    return ""


def fetch(url: str, dst: Path, retries: int = 3) -> bool:
    for i in range(retries):
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "pillsnap-dataset-builder"})
            with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as f:
                f.write(r.read())
            return True
        except Exception:
            time.sleep(2 ** i)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pillbox-csv", required=True)
    ap.add_argument("--out", default="data/c3pi")
    ap.add_argument("--image-base", default="https://data.lhncbc.nlm.nih.gov/public/Pills/PillProjectDisc1/images/")
    ap.add_argument("--max-classes", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    out = Path(args.out)
    rng = random.Random(args.seed)
    groups: dict[str, list[dict]] = {}
    with open(args.pillbox_csv, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            if col(row, "image"):
                groups.setdefault(col(row, "id"), []).append(row)
    ids = list(groups)[: args.max_classes]
    manifest, catalog = [], []
    for n, pid in enumerate(ids):
        rows = groups[pid]
        r0 = rows[0]
        shape = SHAPE_MAP.get(col(r0, "shape").split(";")[0].upper(), "")
        colors = [COLOR_MAP[c] for c in col(r0, "color").upper().replace(",", ";").split(";") if c in COLOR_MAP] or ["white"]
        if shape not in SHAPES or colors[0] not in COLORS:
            continue
        pill_id = re.sub(r"[^a-z0-9-]", "-", pid.lower())
        catalog.append({"pill_id": pill_id, "drug_id": re.sub(r"[^a-z]", "", col(r0, "name").split()[0].lower()) if col(r0, "name") else "unknown", "brand": col(r0, "name"), "strength": col(r0, "strength"), "manufacturer": col(r0, "maker"), "market": "US", "shape": shape, "colors": colors, "imprint": col(r0, "imprint").replace(";", " "), "size_mm": float(col(r0, "size") or 10), "dosage_form": "tablet", "gtin": None, "ndc": pid, "appearance_source": "pillbox"})
        imgs = [col(r, "image") for r in rows]
        rng.shuffle(imgs)
        for j, name in enumerate(imgs):
            fn = name if name.lower().endswith((".jpg", ".png")) else name + ".jpg"
            dst = out / "images" / pill_id / fn
            if not dst.exists() and not fetch(args.image_base + fn, dst):
                continue
            split = "ref" if j == 0 else rng.choices(["train", "val", "test"], [0.7, 0.15, 0.15])[0]
            manifest.append({"path": str(dst.relative_to(out)), "split": split, "pill_id": pill_id, "shape": shape, "color": colors[0]})
        if n % 50 == 0:
            print(f"{n}/{len(ids)} products, {len(manifest)} images")
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest))
    (out / "catalog_pills.json").write_text(json.dumps({"pills": catalog}, indent=1))
    print(f"done: {len(catalog)} products, {len(manifest)} images -> {out}")


if __name__ == "__main__":
    main()
