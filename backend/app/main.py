"""PillSnap API (FastAPI).

    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import safety
from app.config import ALLOWED_ORIGINS, MAX_UPLOAD_MB
from app.content import DISPOSAL
from app.drugs.catalog import Catalog
from app.drugs.llm import Explainer
from app.drugs.rag import DrugRAG
from app.pipeline.ocr import read_imprint
from app.pipeline.pipeline import PillPipeline
from app.pipeline.preprocess import decode_image, resize_max

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
Lang = Literal["en", "hi"]
STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    catalog = Catalog()
    rag = DrugRAG(catalog)
    STATE.update(catalog=catalog, pipeline=PillPipeline(catalog), rag=rag, explainer=Explainer(rag))
    yield


app = FastAPI(title="PillSnap API", version="1.0.0", lifespan=lifespan, description="Pill identification with a multi-step AI pipeline. Information only, never doses.")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_origin_regex=r"https://.*\.vercel\.app", allow_methods=["*"], allow_headers=["*"])


async def _read_upload(f: UploadFile) -> bytes:
    data = await f.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Image is larger than {MAX_UPLOAD_MB} MB")
    if not data:
        raise HTTPException(400, "Empty upload")
    return data


@app.get("/api/health")
def health():
    return {"ok": True, **STATE["pipeline"].status(), "explainer": STATE["explainer"].mode}


@app.post("/api/identify")
async def identify(image: UploadFile = File(...), lang: Lang = Form("en")):
    data = await _read_upload(image)
    try:
        return await run_in_threadpool(STATE["pipeline"].identify, data, lang)
    except ValueError as e:
        raise HTTPException(400, str(e))


class ConfirmIn(BaseModel):
    scan_id: str | None = None
    imprint: str | None = Field(None, max_length=40)
    barcode: str | None = Field(None, max_length=40)
    lang: Lang = "en"


@app.post("/api/confirm")
async def confirm(body: ConfirmIn):
    cat: Catalog = STATE["catalog"]
    if body.barcode:
        p = cat.by_barcode(body.barcode)
        if not p:
            return {"status": "no_match", "matches": [], "message": {"en": "This barcode is not in our database yet. Type the imprint or scan the text on the box instead.", "hi": "यह बारकोड अभी हमारे डेटाबेस में नहीं है। इसके बजाय गोली पर छपे अक्षर टाइप करें या डिब्बे का टेक्स्ट स्कैन करें।"}[body.lang], "disclaimer": safety.DISCLAIMER[body.lang]}
        return {"status": "confident", "matches": [{"pill": cat.public_pill(p, body.lang), "confidence": 0.99, "evidence": {"barcode": True}}], "confirmed_by": "barcode", "disclaimer": safety.DISCLAIMER[body.lang]}
    if not body.imprint:
        raise HTTPException(400, "Send an imprint or a barcode")
    res = await run_in_threadpool(STATE["pipeline"].confirm, body.scan_id, body.imprint, body.lang)
    res["confirmed_by"] = "imprint"
    return res


@app.post("/api/scan-pack")
async def scan_pack(image: UploadFile = File(...), lang: Lang = Form("en")):
    """Read the text on a strip or box (brand, generic name, strength) and match it."""
    data = await _read_upload(image)
    img = resize_max(decode_image(data), 1280)
    ocr = await run_in_threadpool(read_imprint, img)
    text = " ".join(c["text"] for c in ocr.get("candidates", [])) or ocr["text"]
    hits = STATE["catalog"].search_text(text)
    matches = [{"pill": STATE["catalog"].public_pill(p, lang), "confidence": round(min(s, 0.99), 3), "evidence": {"pack_text": True}} for p, s in hits[:3]]
    status = "confident" if matches and matches[0]["confidence"] >= safety.CONFIDENCE_THRESHOLD and (len(matches) == 1 or matches[0]["confidence"] - matches[1]["confidence"] > 0.1) else ("needs_confirmation" if matches else "no_match")
    return {"status": status, "read_text": ocr["text"], "matches": matches, "confirmed_by": "pack_text", "message": None if status == "confident" else safety.LOW_CONFIDENCE_MESSAGE[lang], "disclaimer": safety.DISCLAIMER[lang]}


@app.get("/api/drug/{pill_id}")
async def drug(pill_id: str, lang: Lang = "en"):
    if pill_id not in STATE["catalog"].by_id:
        raise HTTPException(404, "Unknown pill")
    return await run_in_threadpool(STATE["explainer"].explain, pill_id, lang)


class AskIn(BaseModel):
    pill_id: str
    question: str = Field(..., min_length=2, max_length=300)
    lang: Lang = "en"


@app.post("/api/ask")
async def ask(body: AskIn):
    if body.pill_id not in STATE["catalog"].by_id:
        raise HTTPException(404, "Unknown pill")
    return await run_in_threadpool(STATE["explainer"].ask, body.pill_id, body.question, body.lang)


@app.get("/api/pills")
def pills(lang: Lang = "en"):
    cat: Catalog = STATE["catalog"]
    return {"pills": [cat.public_pill(p, lang) for p in cat.pills]}


@app.get("/api/disposal")
def disposal(lang: Lang = "en"):
    return DISPOSAL[lang]
