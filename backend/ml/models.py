"""PillNet: one backbone, three heads.

- embedding head  -> 128-d L2-normalised vector, trained with batch-hard triplet loss
                     plus a normalised-softmax proxy loss (metric learning). Used to match a photo against the pill gallery
                     in FAISS, so new pills can be added without retraining.
- shape head      -> softmax over SHAPES (cross-entropy)
- colour head     -> softmax over COLORS for the dominant colour (cross-entropy)

Backbones: resnet18 / resnet50 / efficientnet_b0 / mobilenet_v3_large from torchvision.
With --pretrained the ImageNet weights are downloaded and fine-tuned (recommended for
real C3PI/ePillID training). Without internet the backbone trains from scratch.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tvm

from app.config import COLORS, SHAPES


def build_backbone(name: str, pretrained: bool) -> tuple[nn.Module, int]:
    weights = "DEFAULT" if pretrained else None
    if name == "resnet18":
        m = tvm.resnet18(weights=weights)
        dim = m.fc.in_features
        m.fc = nn.Identity()
    elif name == "resnet50":
        m = tvm.resnet50(weights=weights)
        dim = m.fc.in_features
        m.fc = nn.Identity()
    elif name == "efficientnet_b0":
        m = tvm.efficientnet_b0(weights=weights)
        dim = m.classifier[1].in_features
        m.classifier = nn.Identity()
    elif name == "mobilenet_v3_large":
        m = tvm.mobilenet_v3_large(weights=weights)
        dim = m.classifier[0].in_features
        m.classifier = nn.Identity()
    else:
        raise ValueError(f"unknown backbone {name}")
    return m, dim


class PillNet(nn.Module):
    def __init__(self, backbone: str = "resnet18", emb_dim: int = 128, pretrained: bool = False, n_classes: int = 0):
        super().__init__()
        self.backbone_name = backbone
        self.backbone, feat = build_backbone(backbone, pretrained)
        self.embed = nn.Sequential(nn.Linear(feat, 256), nn.BatchNorm1d(256), nn.ReLU(inplace=True), nn.Linear(256, emb_dim))
        self.shape_head = nn.Sequential(nn.Dropout(0.2), nn.Linear(feat, len(SHAPES)))
        self.color_head = nn.Sequential(nn.Dropout(0.2), nn.Linear(feat, len(COLORS)))
        # Class proxies for the normalised-softmax loss (training only; matching uses the
        # FAISS gallery, so new pills need no proxy). This keeps the embedding space spread
        # out; triplet loss alone tends to collapse it on small datasets.
        self.proxies = nn.Parameter(torch.randn(n_classes, emb_dim) * 0.1) if n_classes else None

    def forward(self, x):
        f = self.backbone(x)
        emb = F.normalize(self.embed(f), dim=1)
        return emb, self.shape_head(f), self.color_head(f)


def batch_hard_triplet_loss(emb: torch.Tensor, labels: torch.Tensor, margin: float = 0.2) -> torch.Tensor:
    """Hermans et al. 2017: for each anchor take the hardest positive and hardest negative."""
    dist = torch.cdist(emb, emb, p=2)
    same = labels[:, None] == labels[None, :]
    eye = torch.eye(len(labels), dtype=torch.bool, device=emb.device)
    pos = dist.masked_fill(~(same & ~eye), -1).max(1).values
    neg = dist.masked_fill(same, float("inf")).min(1).values
    valid = (pos >= 0) & torch.isfinite(neg)
    if valid.sum() == 0:
        return emb.sum() * 0
    return F.relu(pos[valid] - neg[valid] + margin).mean()


def proxy_softmax_loss(emb: torch.Tensor, labels: torch.Tensor, proxies: torch.Tensor, scale: float = 16.0) -> torch.Tensor:
    """Normalised softmax (cosine classifier) loss, as in NormFace / proxy-based metric learning."""
    logits = scale * emb @ F.normalize(proxies, dim=1).T
    return F.cross_entropy(logits, labels)


def save_model(model: PillNet, path, extra: dict | None = None):
    n_cls = model.proxies.shape[0] if model.proxies is not None else 0
    torch.save({"state_dict": model.state_dict(), "backbone": model.backbone_name, "emb_dim": model.embed[-1].out_features, "n_classes": n_cls, "shapes": SHAPES, "colors": COLORS, **(extra or {})}, path)


def load_model(path, map_location="cpu") -> tuple[PillNet, dict]:
    ck = torch.load(path, map_location=map_location, weights_only=False)
    m = PillNet(ck["backbone"], ck["emb_dim"], pretrained=False, n_classes=ck.get("n_classes", 0))
    m.load_state_dict(ck["state_dict"])
    m.eval()
    return m, ck
