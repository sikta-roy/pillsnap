import numpy as np

from app.pipeline import features as F
from app.pipeline.ocr import imprint_similarity
from app.pipeline.preprocess import preprocess
from ml.synth import load_catalogue, render_pill


def _bgr(rec, seed=0):
    img, _ = render_pill(rec, np.random.default_rng(seed), 256)
    return np.array(img)[..., ::-1].copy()


def test_imprint_similarity_handles_ocr_confusions():
    assert imprint_similarity("D0LO 650", "DOLO 650") == 1.0  # O vs 0
    assert imprint_similarity("dolo650", "DOLO 650") == 1.0
    assert imprint_similarity("650", "DOLO 650") > 0.6
    assert imprint_similarity("XYZ", "DOLO 650") < 0.4


def test_segmentation_finds_pill():
    cat = {p["pill_id"]: p for p in load_catalogue()}
    found = sum(preprocess(_bgr(cat[k], s)).found for k in ("dolo-650", "brufen-400", "pan-40") for s in range(3))
    assert found >= 8


def test_classical_shape_round_vs_oblong():
    cat = {p["pill_id"]: p for p in load_catalogue()}
    r = preprocess(_bgr(cat["brufen-400"], 1))
    o = preprocess(_bgr(cat["dolo-650"], 1))
    assert max(F.classical_shape(r.contour_stats), key=F.classical_shape(r.contour_stats).get) == "round"
    assert max(F.classical_shape(o.contour_stats), key=F.classical_shape(o.contour_stats).get) in ("oblong", "capsule")


def test_classical_colour():
    cat = {p["pill_id"]: p for p in load_catalogue()}
    pre = preprocess(_bgr(cat["voveran-50"], 2))
    col = F.classical_colors(pre.crop_raw, pre.mask)
    assert max(col, key=col.get) == "green"
