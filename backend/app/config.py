"""Central settings. Everything can be overridden with environment variables."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "app" / "data"
ARTIFACTS_DIR = Path(os.getenv("PILLSNAP_ARTIFACTS", BACKEND_DIR / "artifacts"))

# Vocabularies shared by the synthetic renderer, the CNN heads and the matcher.
SHAPES = ["round", "oval", "oblong", "capsule", "rectangle", "diamond", "triangle"]
COLORS = ["white", "yellow", "orange", "pink", "red", "brown", "green", "blue", "purple"]

# Reference RGB values for colour naming (classical colour detector + renderer).
COLOR_RGB = {
    "white": (238, 236, 230),
    "yellow": (236, 205, 80),
    "orange": (236, 140, 60),
    "pink": (236, 160, 180),
    "red": (190, 45, 50),
    "brown": (140, 90, 55),
    "green": (80, 160, 95),
    "blue": (70, 120, 200),
    "purple": (130, 80, 160),
}

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'pillsnap.db'}")
# Hosted Postgres (Render, Supabase, ...) hands out postgres:// URLs; use the psycopg 3 driver.
for _prefix in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(_prefix):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(_prefix):]

# --- Safety ---------------------------------------------------------------
# Below this calibrated probability we never present a single answer.
CONFIDENCE_THRESHOLD = float(os.getenv("PILLSNAP_CONFIDENCE_THRESHOLD", "0.70"))
# Many pills look alike. Without a readable imprint, cap confidence just under the
# threshold so the user is always asked to confirm.
NO_IMPRINT_CONFIDENCE_CAP = 0.69

# --- Models ---------------------------------------------------------------
MODEL_PATH = ARTIFACTS_DIR / "pillnet.pt"
INDEX_PATH = ARTIFACTS_DIR / "pill_index.faiss"
INDEX_META_PATH = ARTIFACTS_DIR / "pill_index_meta.json"
CALIBRATION_PATH = ARTIFACTS_DIR / "calibration.json"
IMAGE_SIZE = int(os.getenv("PILLSNAP_IMAGE_SIZE", "128"))
OCR_ENABLED = os.getenv("PILLSNAP_OCR", "1") == "1"
OCR_GPU = os.getenv("PILLSNAP_OCR_GPU", "0") == "1"

# --- LLM ------------------------------------------------------------------
LLM_MODEL = os.getenv("PILLSNAP_LLM_MODEL", "claude-opus-5-5")
LLM_ENABLED = os.getenv("PILLSNAP_LLM", "auto")  # auto | on | off

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("PILLSNAP_CORS", "http://localhost:3000").split(",") if o.strip()]
MAX_UPLOAD_MB = 12
