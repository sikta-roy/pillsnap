"""Create tables and load app/data/*.json into the database (PostgreSQL or SQLite).

    DATABASE_URL=postgresql+psycopg://pillsnap:pillsnap@localhost:5432/pillsnap python scripts/seed_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy.orm import Session  # noqa: E402

from app.drugs.db import engine, init_db, seed_from_json  # noqa: E402

init_db(seed=False)
with Session(engine) as s:
    seed_from_json(s)
print("seeded", engine.url.render_as_string(hide_password=True))
