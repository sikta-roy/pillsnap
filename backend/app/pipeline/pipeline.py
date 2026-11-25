"""The full identification pipeline: cleanup -> features -> OCR -> matching -> safety."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import asdict

import cv2
import numpy as np

from app import safety
from app.config import COLORS, IMAGE_SIZE, INDEX_META_PATH, INDEX_PATH, MODEL_PATH, SHAPES
from app.drugs.catalog import Catalog
from app.pipeline import features as F
from app.pipeline.matcher import load_temperature, score_candidates
from app.pipeline.ocr import imprint_similarity, ocr_available, read_imprint
from app.pipeline.preprocess import decode_image, preprocess, to_data_url

log = logging.getLogger(__name__)

MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


class PillPipeline:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.model = None
        self.index = None
        self.index_ids: list[str] = []
        self.img_size = IMAGE_SIZE
        self.temperature = load_temperature()
        self._scans: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._load_model()

    # ------------------------------------------------------------------ setup
    def _load_model(self):
        try:
            import faiss
            import torch

            from ml.models import load_model

            if MODEL_PATH.exists() and INDEX_PATH.exists():
                torch.set_num_threads(max(1, torch.get_num_threads()))
                self.model, ck = load_model(MODEL_PATH)
                self.img_size = ck.get("img_size", IMAGE_SIZE)
                self.index = faiss.read_index(str(INDEX_PATH))
                self.index_ids = json.loads(INDEX_META_PATH.read_text())["pill_ids"]
                log.info("PillNet loaded (%s, %d gallery images)", ck["backbone"], self.index.ntotal)
            else:
                log.warning("No trained model/index in artifacts/: running with classical features + OCR only")
        except Exception as e:  # pragma: no cover
            log.warning("Could not load PillNet: %s", e)
            self.model = None

    def status(self) -> dict:
        return {
            "embedding_model": self.model is not None,
            "gallery_images": int(self.index.ntotal) if self.index is not None else 0,
            "ocr": ocr_available(),
            "temperature": self.temperature,
            "catalog_pills": len(self.catalog.pills),
        }

    # -------------------------------------------------------------- inference
    def _cnn(self, crop: np.ndarray):
        import torch

        rgb = cv2.cvtColor(cv2.resize(crop, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        x = torch.from_numpy(((rgb - MEAN) / STD).transpose(2, 0, 1).copy())[None]
        # test-time augmentation: the pill is upright, so also look at it rotated 180°
        x = torch.cat([x, torch.flip(x, dims=[2, 3])])
        with torch.no_grad():
            emb, ps, pc = self.model(x)
        emb = torch.nn.functional.normalize(emb.mean(0, keepdim=True), dim=1).numpy().astype("float32")
        shape = dict(zip(SHAPES, ps.softmax(1).mean(0).tolist()))
        color = dict(zip(COLORS, pc.softmax(1).mean(0).tolist()))
        return emb, shape, color

    def _emb_sims(self, emb: np.ndarray, k: int = 200) -> dict[str, float]:
        k = min(k, self.index.ntotal)
        D, I = self.index.search(emb, k)
        sims: dict[str, float] = {}
        for d, i in zip(D[0], I[0]):
            pid = self.index_ids[i]
            sims[pid] = max(sims.get(pid, -1.0), float(d))
        return sims

    def identify(self, image_bytes: bytes, lang: str = "en") -> dict:
        t0 = time.time()
        img = decode_image(image_bytes)
        pre = preprocess(img, out_size=256)
        timings = {"preprocess_ms": round((time.time() - t0) * 1000)}

        t = time.time()
        classical_color = F.classical_colors(pre.crop_raw, pre.mask)
        classical_shape = F.classical_shape(pre.contour_stats, two_tone=F.is_two_tone(classical_color))
        emb, cnn_shape, cnn_color = (None, None, None)
        if self.model is not None:
            emb, cnn_shape, cnn_color = self._cnn(pre.crop)
        shape_probs = F.fuse(cnn_shape, classical_shape)
        color_probs = F.fuse(cnn_color, classical_color, w_cnn=0.5)
        timings["features_ms"] = round((time.time() - t) * 1000)

        t = time.time()
        ocr = read_imprint(pre.crop_raw, pre.mask if pre.found else None)
        timings["ocr_ms"] = round((time.time() - t) * 1000)

        emb_sims = self._emb_sims(emb) if emb is not None else None
        scan_id = uuid.uuid4().hex[:16]
        state = {
            "shape_probs": shape_probs,
            "color_probs": color_probs,
            "emb_sims": emb_sims,
            "ocr": ocr,
            "crop": to_data_url(pre.crop),
            "found": pre.found,
            "quality": pre.quality,
            "cnn": {"shape": cnn_shape, "color": cnn_color},
            "classical": {"shape": classical_shape, "color": classical_color},
        }
        with self._lock:
            self._scans[scan_id] = state
            while len(self._scans) > 300:
                self._scans.popitem(last=False)
        result = self._rank(state, ocr["text"], ocr["confidence"], lang)
        result.update({"scan_id": scan_id, "timings": {**timings, "total_ms": round((time.time() - t0) * 1000)}})
        return result

    def confirm(self, scan_id: str | None, imprint: str | None, lang: str = "en") -> dict:
        """Re-rank an earlier scan with an imprint typed by the user."""
        state = self._scans.get(scan_id or "")
        if state is None:
            # no photo: rank purely on the typed imprint
            state = {"shape_probs": {s: 1 / len(SHAPES) for s in SHAPES}, "color_probs": {c: 1 / len(COLORS) for c in COLORS}, "emb_sims": None, "ocr": {"text": "", "confidence": 0.0, "engine": "user"}, "crop": None, "found": True, "quality": {}, "cnn": {}, "classical": {}}
        res = self._rank(state, imprint or "", 1.0 if imprint else 0.0, lang, user_imprint=bool(imprint))
        res["scan_id"] = scan_id
        return res

    # ---------------------------------------------------------------- ranking
    def _rank(self, state: dict, imprint_text: str, imprint_conf: float, lang: str, user_imprint: bool = False) -> dict:
        pills = self.catalog.pills
        ranked = score_candidates(pills, state["shape_probs"], state["color_probs"], state["emb_sims"], imprint_text, imprint_conf, self.temperature)
        matches = []
        for p, prob, ev in ranked[:3]:
            matches.append({"pill": self.catalog.public_pill(p, lang), "confidence": round(prob, 3), "evidence": {k: (round(v, 3) if v is not None else None) for k, v in asdict(ev).items()}})
        top_imprint_sim = imprint_similarity(imprint_text, ranked[0][0]["imprint"]) if imprint_text else None
        status, matches = safety.decide(matches, imprint_read=bool(imprint_text), imprint_match=top_imprint_sim)
        if not state["found"] and not user_imprint:
            status = "needs_confirmation"
        tips = []
        q = state.get("quality", {})
        if not state["found"]:
            tips.append("no_pill_found")
        tips += q.get("issues", [])
        if not imprint_text:
            tips.append("imprint_not_read")
        return {
            "status": status,
            "threshold": safety.CONFIDENCE_THRESHOLD,
            "message": safety.LOW_CONFIDENCE_MESSAGE[lang] if status != "confident" else None,
            "matches": matches,
            "detected": {
                "shape": F.top(state["shape_probs"]),
                "color": F.top(state["color_probs"]),
                "imprint": {"text": imprint_text, "confidence": round(imprint_conf, 3), "source": "you typed it" if user_imprint else state["ocr"].get("engine", "")},
                "methods": {
                    "embedding_model": state["emb_sims"] is not None,
                    "cnn_shape": F.top(state["cnn"]["shape"]) if state.get("cnn", {}).get("shape") else None,
                    "classical_shape": F.top(state["classical"]["shape"]) if state.get("classical", {}).get("shape") else None,
                },
                "cleaned_image": state.get("crop"),
            },
            "photo_tips": tips,
            "disclaimer": safety.DISCLAIMER[lang],
        }
