"""Evaluate PillNet as the API uses it: retrieval against a reference gallery.

    python -m ml.evaluate --data data/synth

Reports (written to artifacts/eval/):
- metrics.json            top-1 / top-3 / top-5 retrieval accuracy, shape and colour accuracy,
                          calibrated expected calibration error (ECE)
- confusion_matrix.png    pill-level confusion matrix (top-1)
- shape_confusion.png     shape head confusion matrix
- per_class.csv           per-pill accuracy
Also fits the softmax temperature used to turn match scores into confidences
(artifacts/calibration.json), on the *val* split only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import confusion_matrix
from torch.utils.data import DataLoader

from app.config import ARTIFACTS_DIR, CALIBRATION_PATH, COLORS, MODEL_PATH, SHAPES
from ml.datasets import PillDataset, load_manifest
from ml.models import load_model


@torch.no_grad()
def embed_split(model, ds, device="cpu"):
    E, Y, PS, PC, S, C = [], [], [], [], [], []
    for x, y, s, c in DataLoader(ds, batch_size=64):
        e, ps, pc = model(x.to(device))
        E.append(e.cpu())
        PS.append(ps.softmax(1).cpu())
        PC.append(pc.softmax(1).cpu())
        Y.append(y)
        S.append(s)
        C.append(c)
    return [torch.cat(t).numpy() for t in (E, Y, PS, PC, S, C)]


def fused_logits(E, PS, PC, G, G_lab, n_cls, cls_shape, cls_color, w_emb=1.0, w_attr=0.15):
    """Same fusion as app/pipeline/matcher.py (without the imprint term, which needs OCR)."""
    sim = E @ G.T
    per_cls = np.full((len(E), n_cls), -1.0, np.float32)
    for c in range(n_cls):
        m = G_lab == c
        if m.any():
            per_cls[:, c] = sim[:, m].max(1)
    shape_p = PS[:, cls_shape]
    color_p = PC[:, cls_color]
    return w_emb * per_cls + w_attr * (shape_p + color_p)


def softmax(z, T):
    z = z / T
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def fit_temperature(logits, y):
    best = (1e9, 1.0)
    for T in np.geomspace(0.005, 1.0, 120):
        p = softmax(logits, T)
        nll = -np.log(p[np.arange(len(y)), y] + 1e-12).mean()
        best = min(best, (nll, T))
    return float(best[1])


def ece(probs, y, bins=10):
    conf, pred = probs.max(1), probs.argmax(1)
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            e += m.mean() * abs((pred[m] == y[m]).mean() - conf[m].mean())
    return float(e)


def plot_cm(cm, labels, path, title):
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.38), max(5, len(labels) * 0.36)))
    cmn = cm / np.maximum(cm.sum(1, keepdims=True), 1)
    ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=90, fontsize=7)
    ax.set_yticks(range(len(labels)), labels, fontsize=7)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if cm[i, j]:
                ax.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=6, color="white" if cmn[i, j] > 0.5 else "black")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synth")
    ap.add_argument("--model", default=str(MODEL_PATH))
    ap.add_argument("--out", default=str(ARTIFACTS_DIR / "eval"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    model, ck = load_model(args.model)
    classes, size = ck["classes"], ck["img_size"]
    root = Path(args.data)
    rows = load_manifest(root)
    attrs = {r["pill_id"]: (SHAPES.index(r["shape"]), COLORS.index(r["color"])) for r in rows}
    cls_shape = np.array([attrs[c][0] for c in classes])
    cls_color = np.array([attrs[c][1] for c in classes])

    def ds(split):
        return PillDataset(root, [r for r in rows if r["split"] == split], classes, size, train=False)

    G, G_lab, *_ = embed_split(model, ds("ref"))
    results = {}
    for split in ("val", "test"):
        E, Y, PS, PC, S, C = embed_split(model, ds(split))
        results[split] = (fused_logits(E, PS, PC, G, G_lab, len(classes), cls_shape, cls_color), Y, PS, PC, S, C)

    T = fit_temperature(results["val"][0], results["val"][1])
    CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIBRATION_PATH.write_text(json.dumps({"temperature": T, "fitted_on": "val", "data": str(root)}, indent=2))

    logits, Y, PS, PC, S, C = results["test"]
    probs = softmax(logits, T)
    rank = np.argsort(-probs, 1)
    topk = {f"top{k}_accuracy": float((rank[:, :k] == Y[:, None]).any(1).mean()) for k in (1, 3, 5)}
    pred = rank[:, 0]
    conf = probs.max(1)
    thr = 0.70
    confident = conf >= thr
    metrics = {
        "n_test": int(len(Y)),
        "n_classes": len(classes),
        "gallery_images": int(len(G)),
        **topk,
        "shape_accuracy": float((PS.argmax(1) == S).mean()),
        "color_accuracy": float((PC.argmax(1) == C).mean()),
        "temperature": T,
        "ece": ece(probs, Y),
        "coverage_at_0.70": float(confident.mean()),
        "accuracy_when_confident_at_0.70": float((pred[confident] == Y[confident]).mean()) if confident.any() else None,
        "note": "Imprint OCR is not included here; with a readable imprint the fused score is stronger.",
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    cm = confusion_matrix(Y, pred, labels=range(len(classes)))
    plot_cm(cm, classes, out / "confusion_matrix.png", f"Pill match confusion (top-1 = {topk['top1_accuracy']:.1%})")
    plot_cm(confusion_matrix(S, PS.argmax(1), labels=range(len(SHAPES))), SHAPES, out / "shape_confusion.png", "Shape classifier")
    plot_cm(confusion_matrix(C, PC.argmax(1), labels=range(len(COLORS))), COLORS, out / "color_confusion.png", "Colour classifier")
    with open(out / "per_class.csv", "w") as f:
        f.write("pill_id,n,top1,top3\n")
        for i, c in enumerate(classes):
            m = Y == i
            if m.any():
                f.write(f"{c},{m.sum()},{(pred[m] == i).mean():.3f},{(rank[m, :3] == i).any(1).mean():.3f}\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
