"""Pull official label sections from openFDA into the label_sections table (RAG source).

    python scripts/ingest_openfda.py                 # all drugs in the database
    python scripts/ingest_openfda.py --drug metformin

Sections kept: indications, adverse reactions, warnings, contraindications, do-not-use,
ask-a-doctor, stop-use, storage. Dosage sections are deliberately NOT ingested, and any
sentence that looks like a dosing instruction is removed (PillSnap never gives doses).
Set OPENFDA_API_KEY for higher rate limits.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.drugs.db import Drug, LabelSection, engine, init_db  # noqa: E402
from app.safety import strip_doses  # noqa: E402

SECTIONS = ["indications_and_usage", "purpose", "adverse_reactions", "warnings", "warnings_and_cautions", "boxed_warning", "contraindications", "do_not_use", "ask_doctor", "stop_use", "storage_and_handling", "pregnancy_or_breast_feeding"]
SEARCH_NAME = {"paracetamol": "acetaminophen"}


def fetch_label(generic: str) -> dict | None:
    q = urllib.parse.quote(f'openfda.generic_name:"{generic}"')
    url = f"https://api.fda.gov/drug/label.json?search={q}&limit=1"
    if os.getenv("OPENFDA_API_KEY"):
        url += f"&api_key={os.environ['OPENFDA_API_KEY']}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            res = json.loads(r.read())["results"]
            return res[0] if res else None
    except Exception as e:
        print(f"  ! {generic}: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drug")
    args = ap.parse_args()
    init_db()
    with Session(engine) as s:
        drugs = list(s.scalars(select(Drug)))
        for d in drugs:
            if args.drug and d.id != args.drug:
                continue
            generic = SEARCH_NAME.get(d.id, d.id)
            label = fetch_label(generic)
            if not label:
                continue
            setid = label.get("set_id", "")
            s.execute(delete(LabelSection).where(LabelSection.drug_id == d.id))
            n = 0
            for sec in SECTIONS:
                for text in label.get(sec, []):
                    clean = strip_doses(" ".join(text.split()))
                    if clean:
                        s.add(LabelSection(drug_id=d.id, section=sec, text=clean[:6000], source=f"openFDA drug label ({generic}), set_id {setid}"))
                        n += 1
            s.commit()
            print(f"{d.id}: {n} sections")
            time.sleep(0.3)


if __name__ == "__main__":
    main()
