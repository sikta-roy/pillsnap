"""Train PillNet (metric learning + shape + colour heads).

    python -m ml.train --data data/synth --epochs 12                     # laptop / CPU demo
    python -m ml.train --data data/c3pi --backbone efficientnet_b0 \
        --pretrained --img-size 224 --epochs 40 --device cuda            # real training

Loss = batch-hard triplet + normalised-softmax proxy loss (embedding)
     + lambda * (CE shape + CE colour).
Writes artifacts/pillnet.pt and artifacts/train_log.json.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from app.config import ARTIFACTS_DIR
from ml.datasets import PillDataset, PKSampler, load_manifest
from ml.models import PillNet, batch_hard_triplet_loss, proxy_softmax_loss, save_model


@torch.no_grad()
def quick_val(model, loader, device):
    """Shape/colour accuracy + nearest-neighbour top-1 inside the val set (leave-one-out)."""
    model.eval()
    embs, labels, s_ok, c_ok, n = [], [], 0, 0, 0
    for x, y, s, c in loader:
        e, ps, pc = model(x.to(device))
        embs.append(e.cpu())
        labels.append(y)
        s_ok += (ps.argmax(1).cpu() == s).sum().item()
        c_ok += (pc.argmax(1).cpu() == c).sum().item()
        n += max(1, int((s >= 0).sum()))
    E, Y = torch.cat(embs), torch.cat(labels)
    sim = E @ E.T
    sim.fill_diagonal_(-2)
    nn_acc = (Y[sim.argmax(1)] == Y).float().mean().item()
    model.train()
    return {"nn_top1": nn_acc, "shape_acc": s_ok / n, "color_acc": c_ok / n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synth")
    ap.add_argument("--backbone", default="resnet18")
    ap.add_argument("--pretrained", action="store_true")
    ap.add_argument("--img-size", type=int, default=128)
    ap.add_argument("--emb-dim", type=int, default=128)
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--p", type=int, default=16, help="classes per batch")
    ap.add_argument("--k", type=int, default=4, help="images per class per batch")
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--attr-weight", type=float, default=0.5)
    ap.add_argument("--margin", type=float, default=0.2)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default=str(ARTIFACTS_DIR / "pillnet.pt"))
    args = ap.parse_args()
    torch.manual_seed(0)

    root = Path(args.data)
    rows = load_manifest(root)
    classes = sorted({r["pill_id"] for r in rows})
    train_ds = PillDataset(root, [r for r in rows if r["split"] == "train"], classes, args.img_size, train=True)
    val_ds = PillDataset(root, [r for r in rows if r["split"] == "val"], classes, args.img_size, train=False)
    train_dl = DataLoader(train_ds, batch_sampler=PKSampler(train_ds.labels, args.p, args.k), num_workers=args.workers)
    val_dl = DataLoader(val_ds, batch_size=64, num_workers=args.workers)
    print(f"{len(classes)} classes | train {len(train_ds)} | val {len(val_ds)} | device {args.device}")

    model = PillNet(args.backbone, args.emb_dim, pretrained=args.pretrained, n_classes=len(classes)).to(args.device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    steps = args.epochs * len(train_dl)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps, pct_start=0.15)

    log, best = [], -1.0
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    for ep in range(args.epochs):
        t0, tot = time.time(), {"triplet": 0.0, "shape": 0.0, "color": 0.0}
        for x, y, s, c in train_dl:
            x, y, s, c = x.to(args.device), y.to(args.device), s.to(args.device), c.to(args.device)
            emb, ps, pc = model(x)
            lt = batch_hard_triplet_loss(emb, y, args.margin) + proxy_softmax_loss(emb, y, model.proxies)
            ls = F.cross_entropy(ps, s, label_smoothing=0.05) if (s >= 0).any() else ps.sum() * 0
            lc = F.cross_entropy(pc, c, label_smoothing=0.05) if (c >= 0).any() else pc.sum() * 0
            loss = lt + args.attr_weight * (ls + lc)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            tot["triplet"] += lt.item()
            tot["shape"] += ls.item()
            tot["color"] += lc.item()
        n = len(train_dl)
        val = quick_val(model, val_dl, args.device)
        rec = {"epoch": ep + 1, **{f"loss_{k}": round(v / n, 4) for k, v in tot.items()}, **{k: round(v, 4) for k, v in val.items()}, "sec": round(time.time() - t0, 1)}
        log.append(rec)
        print(json.dumps(rec))
        if val["nn_top1"] >= best:
            best = val["nn_top1"]
            save_model(model, args.out, {"classes": classes, "img_size": args.img_size, "epoch": ep + 1, "val": val})
    (Path(args.out).parent / "train_log.json").write_text(json.dumps({"args": vars(args), "log": log}, indent=2))
    print(f"best val nn_top1={best:.3f} -> {args.out}")


if __name__ == "__main__":
    main()
