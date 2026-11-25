"""Embed the reference gallery and store it in a FAISS index for the API.

    python -m ml.build_index --data data/synth            # uses split == "ref"
    python -m ml.build_index --data data/c3pi --split ref

Adding a new pill = add its reference photos + a catalogue record and rebuild the
index. No retraining is needed, which is the point of the metric-learning design.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
import torch
from torch.utils.data import DataLoader

from app.config import INDEX_META_PATH, INDEX_PATH, MODEL_PATH
from ml.datasets import PillDataset, load_manifest
from ml.models import load_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synth")
    ap.add_argument("--split", default="ref")
    ap.add_argument("--model", default=str(MODEL_PATH))
    args = ap.parse_args()
    model, ck = load_model(args.model)
    root = Path(args.data)
    rows = [r for r in load_manifest(root) if r["split"] == args.split]
    ds = PillDataset(root, rows, sorted({r["pill_id"] for r in rows}), ck["img_size"], train=False)
    embs = []
    with torch.no_grad():
        for x, *_ in DataLoader(ds, batch_size=64):
            embs.append(model(x)[0].numpy())
    E = np.concatenate(embs).astype("float32")
    index = faiss.IndexFlatIP(E.shape[1])  # cosine similarity on L2-normalised vectors
    index.add(E)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    INDEX_META_PATH.write_text(json.dumps({"pill_ids": [r["pill_id"] for r in ds.rows], "paths": [r["path"] for r in ds.rows]}))
    print(f"indexed {index.ntotal} reference images for {len(set(r['pill_id'] for r in ds.rows))} pills -> {INDEX_PATH}")


if __name__ == "__main__":
    main()
