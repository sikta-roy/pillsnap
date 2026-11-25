import io
import os

import numpy as np
import pytest

os.environ.setdefault("PILLSNAP_LLM", "off")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_pillsnap.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from ml.synth import load_catalogue, render_pill  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _jpeg(pill_id: str, seed: int = 0) -> bytes:
    rec = next(p for p in load_catalogue() if p["pill_id"] == pill_id)
    img, _ = render_pill(rec, np.random.default_rng(seed), 320)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def test_health(client):
    r = client.get("/api/health").json()
    assert r["ok"] and r["catalog_pills"] > 20


def test_identify_has_disclaimer_and_top3(client):
    r = client.post("/api/identify", files={"image": ("p.jpg", _jpeg("allegra-120"), "image/jpeg")}, data={"lang": "en"}).json()
    assert r["disclaimer"].startswith("This is for information only")
    assert 1 <= len(r["matches"]) <= 3
    assert r["status"] in ("confident", "needs_confirmation")
    assert {"shape", "color", "imprint"} <= set(r["detected"])
    if r["status"] == "needs_confirmation":
        assert r["message"]


def test_confirm_with_typed_imprint(client):
    r = client.post("/api/confirm", json={"imprint": "pan 40", "lang": "en"}).json()
    assert r["matches"][0]["pill"]["pill_id"] == "pan-40"
    assert r["status"] == "confident"


def test_unknown_barcode(client):
    r = client.post("/api/confirm", json={"barcode": "0000000000", "lang": "hi"}).json()
    assert r["status"] == "no_match" and "फार्मासिस्ट" in r["disclaimer"]


def test_drug_info_grounded_and_dose_free(client):
    from app.safety import contains_dose

    r = client.get("/api/drug/dolo-650").json()
    assert r["overview"]["uses"]
    for sec in (r["overview"]["uses"], r["side_effects"]["common"], r["safety"]["warnings"]):
        for st in sec:
            assert st["source_ids"], st
            assert not contains_dose(st["text"]), st
    assert r["disclaimer"]


def test_ask_refuses_doses(client):
    r = client.post("/api/ask", json={"pill_id": "dolo-650", "question": "How many tablets can I take per day?"}).json()
    assert r["refused"] == "dose"


def test_ask_uses_retrieval(client):
    r = client.post("/api/ask", json={"pill_id": "okacet-10", "question": "Will it make me sleepy?"}).json()
    assert any("sleep" in a["text"].lower() or "drows" in a["text"].lower() for a in r["answer"])


def test_disposal_hindi(client):
    assert "फेंकें" in client.get("/api/disposal?lang=hi").json()["title"]
