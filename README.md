# PillSnap

**Take a photo of a loose pill and learn what it most likely is.** PillSnap reads the pill's shape, colour and imprint, matches it against a pill database with a metric-learning model, and explains the medicine in plain English or Hindi using only trusted drug data.

> ⚠️ **This is for information only. Do not take a pill based only on this app. Ask a pharmacist or doctor.** PillSnap never gives doses.

---

## What it does

| For the user | Under the hood |
| --- | --- |
| Upload or take a photo (phone camera supported) | OpenCV cleanup: white balance, pill segmentation (border background model + Otsu + GrabCut), upright crop, CLAHE |
| Scanning animation, then a result card | **PillNet** (PyTorch): CNN backbone + metric-learning embedding + shape head + colour head |
| Name, strength, maker, confidence | **EasyOCR** reads the imprint (text-angle estimation, 0/180°, inverted pass) |
| Top 3 matches when unsure (< 70%) | **FAISS** nearest-neighbour search over reference photos, fused with shape/colour/imprint, temperature-calibrated |
| Confirm by typing the imprint, scanning the strip/box text, or the barcode | Re-ranking with the typed imprint; OCR + fuzzy match on pack text; barcode lookup (NDC/GTIN) |
| Tabs: Overview, Side effects, Alternatives, Safety | **RAG** over the drug database (TF-IDF + FAISS) and optional **Claude** LLM, which may only restate retrieved facts, each with a citation |
| "How the AI decided" | Detected shape, colour, imprint text, cleaned photo, and per-match evidence scores |
| Safe disposal guide, history on device, English/हिंदी, large text | Static reviewed content, `localStorage`, i18n dictionary, ARIA tabs/labels |

## Screenshots

| Landing | Confident result | Not sure: top 3 + confirm | Hindi on a phone |
| --- | --- | --- | --- |
| ![](docs/screenshots/landing.png) | ![](docs/screenshots/result_confident.png) | ![](docs/screenshots/result_low.png) | ![](docs/screenshots/mobile_result_hi.png) |

## System architecture

```mermaid
flowchart LR
  subgraph Browser["Next.js + Tailwind (Vercel)"]
    UI[Upload / camera] --> SA[Scanning animation] --> RC[Result card + tabs]
    RC --> CF[Confirm: imprint / pack / barcode]
    RC --> HS[(History: localStorage)]
  end

  subgraph API["FastAPI (Render / HF Spaces)"]
    direction TB
    P1["1. Cleanup (OpenCV)<br/>white balance, segment, crop, CLAHE"]
    P2["2. Features<br/>PillNet CNN: embedding + shape + colour<br/>+ classical contour / k-means colour"]
    P3["3. Imprint OCR<br/>EasyOCR (CRAFT + CRNN)"]
    P4["4. Matching<br/>FAISS gallery search + fusion<br/>+ temperature calibration"]
    P5["5. Safety rules<br/>&lt;70% or no imprint → top-3 + confirm<br/>disclaimer, no doses"]
    P1 --> P2 --> P3 --> P4 --> P5
    R1["RAG retriever<br/>TF-IDF + FAISS"] --> L1["LLM explainer (Claude)<br/>cited statements only,<br/>support check, dose filter"]
  end

  DB[(PostgreSQL<br/>drugs, pills, label_sections)]
  VI[(FAISS<br/>pill embeddings)]
  VR[(FAISS<br/>drug-text chunks)]
  SRC[[openFDA / DailyMed<br/>C3PI / Pillbox / ePillID]]

  UI -- "POST /api/identify" --> P1
  CF -- "POST /api/confirm, /api/scan-pack" --> P4
  RC -- "GET /api/drug/{id}, POST /api/ask" --> R1
  P4 <--> VI
  P4 <--> DB
  R1 <--> VR
  R1 <--> DB
  SRC -. "scripts/ingest_*, download_*" .-> DB
  SRC -. "ml/train.py, ml/build_index.py" .-> VI
```

### Why a multi-step pipeline and not one classifier

- **Metric learning instead of a fixed classifier.** PillNet maps a photo to a 128-d vector trained with batch-hard triplet loss plus a normalised-softmax proxy loss (the proxy term stops the embedding space from collapsing, which triplet loss alone did in our first run). Matching is nearest-neighbour search against reference photos, so **adding a new pill (e.g. an Indian brand) only needs reference photos and an index rebuild, not retraining.**
- **Imprint is the strongest signal.** Thousands of pills are small, white and round. The imprint usually decides. That is why confidence is capped below 70% when no imprint is read, and the user is asked to type it.
- **Two detectors for shape and colour.** The CNN heads are fused with classical OpenCV estimates (contour geometry, k-means in Lab), which keeps the app working before a model is trained and acts as a sanity check on unusual photos.
- **Calibrated confidence.** Fused match scores are turned into probabilities with a softmax temperature fitted on the validation split (`artifacts/calibration.json`), so "70%" means something.

## Safety rules (enforced in code)

| Rule | Where |
| --- | --- |
| Disclaimer on every result (EN + HI) | `backend/app/safety.py` → every API response; `frontend/components/Disclaimer.tsx` on every result, scan page and footer |
| Below 70% confidence: no single answer, show top 3 and ask to confirm | `safety.decide()` |
| No readable imprint (or imprint disagrees): confidence capped at 69% | `safety.decide()` |
| Never suggest doses | dosage sections are never ingested; regex dose filter on all generated and ingested text; dose questions get a fixed referral answer (`safety.is_dose_question`) |
| LLM uses only retrieved data | structured output with chunk-id citations; citations must exist; lexical support check per statement; unsupported statements are dropped and counted; extractive fallback (`backend/app/drugs/llm.py`) |
| Safe disposal guidance | `/disposal` page, linked from the Safety tab |

## Folder structure

```
pillsnap/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI routes
│   │   ├── config.py            settings (env vars), vocabularies, thresholds
│   │   ├── safety.py            disclaimer, confidence rules, dose filter
│   │   ├── content.py           disposal guide (EN/HI)
│   │   ├── pipeline/
│   │   │   ├── preprocess.py    step 1: OpenCV cleanup
│   │   │   ├── features.py      step 2: classical shape/colour + fusion
│   │   │   ├── ocr.py           step 3: imprint OCR + imprint similarity
│   │   │   ├── matcher.py       step 4: fused scoring + calibration
│   │   │   └── pipeline.py      orchestration, scan cache for confirmation
│   │   ├── drugs/
│   │   │   ├── db.py            SQLAlchemy models (PostgreSQL / SQLite)
│   │   │   ├── catalog.py       pill catalogue, pack-text and barcode lookup
│   │   │   ├── rag.py           chunking + TF-IDF + FAISS retriever
│   │   │   └── llm.py           grounded explanations (Claude) + guardrails
│   │   └── data/
│   │       ├── drugs.json       22 drugs: plain-language facts, brands (IN/US), sources
│   │       └── pills.json       28 products (Indian + US brands)
│   ├── ml/
│   │   ├── synth.py             synthetic pill photo renderer
│   │   ├── datasets.py          manifest loader, cleanup cache, P×K sampler
│   │   ├── models.py            PillNet + batch-hard triplet loss
│   │   ├── train.py             training loop
│   │   ├── evaluate.py          top-1/3/5, confusion matrices, calibration
│   │   └── build_index.py       FAISS gallery index
│   ├── scripts/
│   │   ├── download_c3pi.py     NLM C3PI / Pillbox → manifest + catalogue
│   │   ├── prepare_epillid.py   ePillID → manifest
│   │   ├── ingest_openfda.py    openFDA label sections → RAG
│   │   ├── seed_db.py           create tables + load JSON
│   │   └── make_samples.py      regenerate sample_images/
│   ├── notebooks/train_pill_model.ipynb
│   ├── artifacts/               trained model, FAISS index, calibration, eval reports
│   ├── tests/                   pytest: safety, guardrails, pipeline, API
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                    Next.js 15 (App Router) + Tailwind
│   ├── app/                     / (landing), /scan, /history, /disposal
│   ├── components/              Header, ResultView, DrugTabs, HowAIDecided, ConfirmPanel, ...
│   └── lib/                     api client, i18n (EN/HI), history
├── sample_images/               test photos (+ a strip photo for "scan the pack")
├── docker-compose.yml           PostgreSQL + API + web
└── render.yaml                  Render blueprint (API + Postgres)
```

## Setup

### Requirements
Python 3.11+ (tested on 3.13), Node 20+ (tested on 22). A GPU is optional.

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu   # or the CUDA build
pip install -r requirements-dev.txt

# (optional) PostgreSQL. Without DATABASE_URL a local SQLite file is used.
export DATABASE_URL=postgresql+psycopg://pillsnap:pillsnap@localhost:5432/pillsnap
python scripts/seed_db.py

# (optional) LLM explanations + Hindi translation. Without a key PillSnap shows
# the retrieved facts directly (extractive mode).
export ANTHROPIC_API_KEY=...

uvicorn app.main:app --reload --port 8000
```

The trained demo model, FAISS index and calibration are already in `backend/artifacts/`, so the API works straight away. The first request downloads the EasyOCR weights (~100 MB) once.

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                     # http://localhost:3000
```

To test the camera on a phone, open the dev server over your LAN (camera capture through the file input works over plain HTTP on most phones; live `getUserMedia` would need HTTPS).

### 3. Everything with Docker

```bash
docker compose up --build       # web :3000, api :8000, postgres :5432
```

### Tests

```bash
cd backend && pytest -q          # safety rules, LLM guardrails, pipeline, API end to end
cd frontend && npm run typecheck && npm run build
```

## Training the pill model

```bash
cd backend
python -m ml.synth --out data/synth --per-class 120      # 1. data (synthetic, ~3 min)
python -m ml.train --data data/synth --epochs 20         # 2. train (~12 min on 4 CPU cores)
python -m ml.evaluate --data data/synth                  # 3. metrics + confusion matrix + calibration
python -m ml.build_index --data data/synth               # 4. FAISS gallery for the API
```

Or open `backend/notebooks/train_pill_model.ipynb`, which runs the same steps with plots (loss curves, confusion matrices, t-SNE of embeddings, full pipeline with OCR).

### Results (demo model, synthetic test set)

Model: ResNet-18 trained from scratch on CPU (20 epochs, 128 px), 28 pills, 2,352 training photos, gallery of 6 reference photos per pill.

| Metric | Embedding + shape/colour only (`ml/evaluate.py`, 504 test photos) | Full pipeline incl. OCR (`ml/eval_pipeline.py`, 120 test photos) |
| --- | --- | --- |
| Top-1 accuracy | 88.5% | 99.2% |
| Top-3 accuracy | 98.4% | 99.2% |
| Shape / colour head accuracy | 98.4% / 99.0% | |
| Expected calibration error | 0.035 | |
| Share answered with one confident result (≥ 70%) | 75.4% | 80.8% |
| Accuracy of those confident answers | 98.9% | 100% |
| Imprint read rate | | 100% |
| Time per photo (4-core CPU) | | 1.2 s |

The rest are shown as "not sure yet" with the top 3 and a request to confirm, which is the intended behaviour.

Reports: `backend/artifacts/eval/metrics.json`, `confusion_matrix.png`, `shape_confusion.png`, `color_confusion.png`, `per_class.csv`.

**Read these numbers honestly.** They are measured on synthetic renders of 28 catalogue pills. They show the pipeline works end to end; they are not real-world accuracy. Real-world accuracy has to be measured on real photos (ePillID consumer images are the standard benchmark).

### Training on real data

| Dataset | What it gives | Script |
| --- | --- | --- |
| NLM C3PI + Pillbox (archived) | ~130k reference photos of US pills with NDC, shape, colour, imprint, strength, maker | `scripts/download_c3pi.py --pillbox-csv pillbox.csv` |
| ePillID | 4,902 classes; reference + real consumer photos (best benchmark) | `scripts/prepare_epillid.py --root ePillID_data` |
| openFDA / DailyMed | official label text for RAG | `scripts/ingest_openfda.py` |
| Indian medicines | no public image set: photograph 6+ reference images per pill on a plain background | add records to `app/data/pills.json`, then `ml.build_index` |

```bash
python -m ml.train --data data/c3pi --backbone efficientnet_b0 --pretrained --img-size 224 --epochs 40 --device cuda
python -m ml.evaluate --data data/epillid
python -m ml.build_index --data data/c3pi
```

The C3PI and ePillID download scripts follow the published formats but were not run in the build environment (those hosts were not reachable), so check the URLs and column names noted at the top of each script before a long run.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/identify` | multipart `image`, `lang` → status, top 3 matches with confidence + evidence, detected shape/colour/imprint, cleaned photo, tips, disclaimer |
| `POST` | `/api/confirm` | `{scan_id, imprint}` or `{barcode}` → re-ranked result |
| `POST` | `/api/scan-pack` | photo of strip/box → OCR text + matched products |
| `GET` | `/api/drug/{pill_id}?lang=` | Overview / Side effects / Alternatives / Safety, each statement with source ids |
| `POST` | `/api/ask` | question about the identified medicine (RAG only; dose questions refused) |
| `GET` | `/api/disposal?lang=` | safe disposal guide |
| `GET` | `/api/pills`, `/api/health` | catalogue, model/OCR/LLM status |

Interactive docs at `http://localhost:8000/docs`.

## Deploy

- **Frontend → Vercel**: import the repo, root directory `frontend`, env `NEXT_PUBLIC_API_URL=https://<your-api>`.
- **Backend → Render**: `render.yaml` creates the API (Docker) and PostgreSQL. Set `PILLSNAP_CORS` to your Vercel URL and optionally `ANTHROPIC_API_KEY`. Use at least the 2 GB plan (PyTorch + EasyOCR).
- **Backend → Hugging Face Spaces**: create a Docker Space and push the `backend/` folder; the Dockerfile listens on 7860. Use an external Postgres via `DATABASE_URL` or keep SQLite.

## Data honesty

- `app/data/drugs.json` facts are summarised in plain language from public label information (openFDA / DailyMed) and Indian package inserts. **Have a pharmacist review them before real use**, or replace them with `scripts/ingest_openfda.py`.
- `app/data/pills.json` lists real products (brand, strength, maker), but **their appearance (shape, colour, imprint) is demo data** used to render the synthetic training set. They are marked `appearance_source: "demo"` and the app shows a note on them. Replace with C3PI records or your own reference photos.
- Photos are processed in memory and not stored. History is kept only in the user's browser.

## Configuration

| Env var | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | SQLite file | PostgreSQL URL (postgres:// is accepted) |
| `PILLSNAP_CONFIDENCE_THRESHOLD` | `0.70` | below this, no single answer |
| `ANTHROPIC_API_KEY` | unset | enables LLM explanations + Hindi translation |
| `PILLSNAP_LLM` | `auto` | `off` forces extractive mode |
| `PILLSNAP_LLM_MODEL` | `claude-opus-5-5` | model for explanations |
| `PILLSNAP_OCR` | `1` | `0` disables OCR |
| `PILLSNAP_CORS` | `http://localhost:3000` | allowed origins (comma separated; `*.vercel.app` allowed) |
