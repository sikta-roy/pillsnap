"""Drug database (PostgreSQL in production, SQLite for local dev).

Tables
- drugs           one row per active ingredient (plain-language facts)
- pills           one row per physical product (brand, strength, maker, appearance)
- label_sections  raw label text ingested from openFDA / DailyMed (scripts/ingest_openfda.py)
"""
from __future__ import annotations

import json

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATA_DIR, DATABASE_URL


class Base(DeclarativeBase):
    pass


class Drug(Base):
    __tablename__ = "drugs"
    id = Column(String(64), primary_key=True)
    generic_name = Column(String(200), nullable=False)
    data = Column(JSON, nullable=False)


class Pill(Base):
    __tablename__ = "pills"
    pill_id = Column(String(64), primary_key=True)
    drug_id = Column(String(64), ForeignKey("drugs.id"), index=True)
    brand = Column(String(200), index=True)
    strength = Column(String(64))
    manufacturer = Column(String(200))
    imprint = Column(String(64), index=True)
    gtin = Column(String(32), index=True, nullable=True)
    ndc = Column(String(32), index=True, nullable=True)
    data = Column(JSON, nullable=False)


class LabelSection(Base):
    __tablename__ = "label_sections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    drug_id = Column(String(64), ForeignKey("drugs.id"), index=True)
    section = Column(String(64))
    text = Column(Text)
    source = Column(String(300))


engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db(seed: bool = True) -> None:
    Base.metadata.create_all(engine)
    if not seed:
        return
    with Session(engine) as s:
        if s.scalar(select(Drug.id).limit(1)) is None:
            seed_from_json(s)


def seed_from_json(s: Session) -> None:
    drugs = json.loads((DATA_DIR / "drugs.json").read_text())["drugs"]
    pills = json.loads((DATA_DIR / "pills.json").read_text())["pills"]
    for d in drugs:
        s.merge(Drug(id=d["id"], generic_name=d["generic_name"], data=d))
    for p in pills:
        s.merge(Pill(pill_id=p["pill_id"], drug_id=p["drug_id"], brand=p["brand"], strength=p["strength"], manufacturer=p["manufacturer"], imprint=p["imprint"], gtin=p.get("gtin"), ndc=p.get("ndc"), data=p))
    s.commit()
