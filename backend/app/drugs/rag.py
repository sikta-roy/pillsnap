"""Retrieval over trusted drug data (RAG).

Knowledge sources, each split into small citable chunks with stable ids:
- curated facts in the drugs table (app/data/drugs.json)
- label sections ingested from openFDA / DailyMed (scripts/ingest_openfda.py)

Chunks are embedded with TF-IDF (word + character n-grams, so it works offline and
handles drug-name spelling variants) and stored in a FAISS inner-product index.
A sentence-embedding model can replace TF-IDF in `_embed` without other changes.
"""
from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_union

from app.drugs.catalog import Catalog

FIELDS = [
    ("uses", "Uses"),
    ("how_it_works", "How it works"),
    ("common_side_effects", "Common side effects"),
    ("serious_side_effects", "Serious side effects"),
    ("who_should_not_take", "Who should not take it"),
    ("warnings", "Warnings"),
    ("storage", "Storage"),
    ("drug_class", "Drug class"),
    ("rx_status", "Prescription status"),
]


@dataclass
class Chunk:
    id: str
    drug_id: str
    section: str
    text: str
    source: str


class DrugRAG:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.chunks: list[Chunk] = []
        for did, d in catalog.drugs.items():
            src = "; ".join(d.get("sources", [])) or "PillSnap curated database"
            name = d["generic_name"]
            for key, title in FIELDS:
                val = d.get(key)
                items = val if isinstance(val, list) else [val] if val else []
                for i, t in enumerate(items):
                    self.chunks.append(Chunk(f"{did}:{key}:{i}", did, key, f"{name}. {title}: {t}", src))
            for region, names in d.get("brands", {}).items():
                self.chunks.append(Chunk(f"{did}:brands:{region}", did, "brands", f"{name}. Brands with the same active ingredient ({region}): {', '.join(names)}", src))
            for i, sm in enumerate(d.get("similar_medicines", [])):
                self.chunks.append(Chunk(f"{did}:similar:{i}", did, "similar_medicines", f"{name}. Similar medicine: {sm['name']}. {sm['note']}", src))
            for i, ls in enumerate(catalog.labels.get(did, [])):
                # long label sections are split into ~600 char windows
                text = ls["text"]
                for j in range(0, len(text), 600):
                    self.chunks.append(Chunk(f"{did}:label:{ls['section']}:{i}:{j // 600}", did, ls["section"], f"{name}. {ls['section']}: {text[j:j + 700]}", ls["source"]))
        self.by_id = {c.id: c for c in self.chunks}
        self.vec = make_union(
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1),
        )
        X = self._embed([c.text for c in self.chunks], fit=True)
        self.index = faiss.IndexFlatIP(X.shape[1])
        self.index.add(X)

    def _embed(self, texts: list[str], fit: bool = False) -> np.ndarray:
        X = self.vec.fit_transform(texts) if fit else self.vec.transform(texts)
        X = X.toarray().astype("float32")
        faiss.normalize_L2(X)
        return X

    def for_drug(self, drug_id: str) -> list[Chunk]:
        return [c for c in self.chunks if c.drug_id == drug_id]

    def search(self, query: str, drug_id: str | None = None, k: int = 6) -> list[tuple[Chunk, float]]:
        q = self._embed([query])
        D, I = self.index.search(q, min(len(self.chunks), 200 if drug_id else k))
        out = []
        for d, i in zip(D[0], I[0]):
            c = self.chunks[i]
            if drug_id and c.drug_id != drug_id:
                continue
            out.append((c, float(d)))
            if len(out) >= k:
                break
        return out
