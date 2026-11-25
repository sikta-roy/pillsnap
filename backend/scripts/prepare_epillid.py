"""Convert the ePillID benchmark (Usuyama et al., CVPR-W 2020) into a PillSnap manifest.

ePillID has 13k images of 4,902 pill appearance classes: studio reference images
(from C3PI) plus real consumer photos, which makes it the best public test of
"phone photo -> reference" matching, the exact task PillSnap solves.

1. Download the dataset release from https://github.com/usuyama/ePillID-benchmark
   (see the README there for the data link) and unzip it.
2. python scripts/prepare_epillid.py --root path/to/ePillID_data --out data/epillid

Reference images (is_ref == 1) become the matching gallery ("ref"); consumer images are
split into train/val/test by pill class so that test classes are seen only via their
reference photos (the realistic setting for new pills). ePillID has no shape/colour
labels, so those heads are trained only on data that has them (labels set to "unknown").
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="folder that contains all_labels.csv and classification_data/")
    ap.add_argument("--out", default="data/epillid")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.out)
    rng = random.Random(args.seed)
    rows = list(csv.DictReader(open(root / "all_labels.csv")))
    classes = sorted({r["pilltype_id"] for r in rows})
    rng.shuffle(classes)
    n = len(classes)
    cls_split = {c: ("train" if i < 0.7 * n else "val" if i < 0.85 * n else "test") for i, c in enumerate(classes)}
    manifest = []
    for r in rows:
        img = root / "classification_data" / r["image_path"]
        if not img.exists():
            continue
        out_path = out / "images" / r["image_path"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not out_path.exists():
            out_path.symlink_to(img.resolve())
        split = "ref" if r.get("is_ref") in ("1", "True", "true") else cls_split[r["pilltype_id"]]
        manifest.append({"path": str(out_path.relative_to(out)), "split": split, "pill_id": r["pilltype_id"], "shape": "unknown", "color": "unknown"})
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest))
    print(f"{len(manifest)} images, {len(classes)} classes -> {out}/manifest.json")


if __name__ == "__main__":
    main()
