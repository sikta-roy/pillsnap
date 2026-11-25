"""End-to-end evaluation of the full pipeline (cleanup + CNN + OCR + matching + safety).

    python -m ml.eval_pipeline --data data/synth --n 120

Slower than ml/evaluate.py because it runs OCR on every photo.
Writes artifacts/eval/pipeline_metrics.json.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path

os.environ.setdefault("PILLSNAP_LLM", "off")

from app.config import ARTIFACTS_DIR  # noqa: E402
from app.drugs.catalog import Catalog  # noqa: E402
from app.pipeline.pipeline import PillPipeline  # noqa: E402
from ml.datasets import load_manifest  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synth")
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    root = Path(args.data)
    rows = [r for r in load_manifest(root) if r["split"] == "test"]
    random.Random(args.seed).shuffle(rows)
    rows = rows[: args.n]
    pipe = PillPipeline(Catalog())
    top1 = top3 = conf_n = conf_ok = imprint_read = 0
    t0 = time.time()
    for r in rows:
        res = pipe.identify((root / r["path"]).read_bytes())
        ids = [m["pill"]["pill_id"] for m in res["matches"]]
        top1 += ids[0] == r["pill_id"]
        top3 += r["pill_id"] in ids
        imprint_read += bool(res["detected"]["imprint"]["text"])
        if res["status"] == "confident":
            conf_n += 1
            conf_ok += ids[0] == r["pill_id"]
    n = len(rows)
    m = {
        "n": n,
        "top1_accuracy": top1 / n,
        "top3_accuracy": top3 / n,
        "imprint_read_rate": imprint_read / n,
        "answered_confidently": conf_n / n,
        "accuracy_when_confident": conf_ok / conf_n if conf_n else None,
        "sec_per_image_cpu": (time.time() - t0) / n,
    }
    out = ARTIFACTS_DIR / "eval" / "pipeline_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
