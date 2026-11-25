"""In-memory view of the drug database used by the pipeline and the API."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.drugs.db import Drug, LabelSection, Pill, engine, init_db
from app.pipeline.ocr import normalize

SHAPE_HI = {"round": "गोल", "oval": "अंडाकार", "oblong": "लंबी (कैपलेट)", "capsule": "कैप्सूल", "rectangle": "आयताकार", "diamond": "हीरे जैसी", "triangle": "त्रिकोणीय"}
COLOR_HI = {"white": "सफ़ेद", "yellow": "पीली", "orange": "नारंगी", "pink": "गुलाबी", "red": "लाल", "brown": "भूरी", "green": "हरी", "blue": "नीली", "purple": "बैंगनी"}


class Catalog:
    def __init__(self):
        init_db()
        with Session(engine) as s:
            self.drugs = {d.id: d.data for d in s.scalars(select(Drug))}
            self.pills = [p.data for p in s.scalars(select(Pill).order_by(Pill.pill_id))]
            self.labels: dict[str, list[dict]] = {}
            for ls in s.scalars(select(LabelSection)):
                self.labels.setdefault(ls.drug_id, []).append({"section": ls.section, "text": ls.text, "source": ls.source})
        self.by_id = {p["pill_id"]: p for p in self.pills}

    def public_pill(self, p: dict, lang: str = "en") -> dict:
        d = self.drugs.get(p["drug_id"], {})
        return {
            "pill_id": p["pill_id"],
            "brand": p["brand"],
            "generic_name": d.get("name_hi") if lang == "hi" and d.get("name_hi") else d.get("generic_name", p["drug_id"]),
            "strength": p["strength"],
            "manufacturer": p["manufacturer"],
            "market": p["market"],
            "shape": SHAPE_HI.get(p["shape"], p["shape"]) if lang == "hi" else p["shape"],
            "colors": [COLOR_HI.get(c, c) for c in p["colors"]] if lang == "hi" else p["colors"],
            "imprint": p["imprint"],
            "dosage_form": p.get("dosage_form"),
            "rx_status": d.get("rx_status"),
            "appearance_source": p.get("appearance_source", "unknown"),
        }

    def search_text(self, text: str, limit: int = 5) -> list[tuple[dict, float]]:
        """Fuzzy match free text (e.g. OCR from a strip/box) against brands, generics, imprints."""
        tokens = [t for t in re.split(r"[^A-Za-z0-9]+", text.upper()) if len(t) >= 2]
        joined = normalize(text)
        scored = []
        for p in self.pills:
            d = self.drugs.get(p["drug_id"], {})
            names = [p["brand"], p["brand"].split()[0], d.get("generic_name", "").split(" (")[0]] + d.get("brands", {}).get("IN", []) + d.get("brands", {}).get("US", [])
            best = 0.0
            for n in names:
                nn = normalize(n)
                if len(nn) < 3:
                    continue
                if nn in joined:
                    best = max(best, 0.9 + 0.1 * (n == p["brand"]))
                for t in tokens:
                    best = max(best, SequenceMatcher(None, t, nn).ratio() * 0.85)
            strength = normalize(p["strength"])
            if best > 0.5 and strength and strength in joined:
                best = min(1.0, best + 0.1)
            if p.get("gtin") and p["gtin"] in joined:
                best = 1.0
            scored.append((p, best))
        scored.sort(key=lambda x: -x[1])
        return [s for s in scored[:limit] if s[1] >= 0.6]

    def by_barcode(self, code: str) -> dict | None:
        code = re.sub(r"\D", "", code or "")
        for p in self.pills:
            for k in ("gtin", "ndc"):
                v = re.sub(r"\D", "", p.get(k) or "")
                if v and (v == code or (len(v) >= 10 and v in code)):
                    return p
        return None
