# storage.py
import os
import json
from datetime import datetime, date
from typing import List, Tuple, Optional, Dict

from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, Float, String, Date, DateTime, Text
)
from sqlalchemy.sql import select, insert, update
from sqlalchemy.pool import NullPool

def _get_db_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        try:
            import streamlit as st
            url = str(st.secrets.get("DATABASE_URL", "")).strip()
        except Exception:
            pass
    return url

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = _get_db_url()
        if db_url:
            _engine = create_engine(db_url, pool_pre_ping=True, poolclass=NullPool)
        else:
            _engine = create_engine("sqlite:///data.db", connect_args={"check_same_thread": False})
    return _engine

metadata = MetaData()

profiles = Table(
    "profiles", metadata,
    Column("user_key", String(80), primary_key=True),
    Column("full_name", String(200), nullable=True),
    Column("phone_last4", String(8), nullable=True),
    Column("age", Integer, nullable=True),
    Column("gender", String(30), nullable=True),
    Column("height_cm", Integer, nullable=True),
    Column("weight_kg", Float, nullable=True),
    Column("family_history_json", Text, nullable=True),
    Column("diabetes_type", String(30), nullable=True),
    Column("has_hypertension", Integer, nullable=True),
    Column("has_high_cholesterol", Integer, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

glucose_logs = Table(
    "glucose_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_key", String(80), nullable=False),
    Column("measured_at", DateTime, nullable=False),
    Column("logged_at", DateTime, nullable=False),
    Column("reading_type", String(40), nullable=False),
    Column("value", Float, nullable=False),
    Column("meal_note", Text, nullable=True),
)

daily_checkins = Table(
    "daily_checkins", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_key", String(80), nullable=False),
    Column("checkin_date", Date, nullable=False),
    Column("followed_plan", Integer, nullable=False),
    Column("actual_meals", Text, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

def init_db() -> None:
    metadata.create_all(get_engine())

def get_profile(user_key: str) -> Optional[Dict]:
    with get_engine().begin() as conn:
        row = conn.execute(
            select(profiles).where(profiles.c.user_key == user_key)
        ).fetchone()
    if not row:
        return None
    d = dict(row._mapping)
    try:
        d["family_history"] = json.loads(d.get("family_history_json") or "[]")
    except Exception:
        d["family_history"] = []
    return d

def upsert_profile(user_key: str, data: Dict) -> None:
    now = datetime.now()
    family_history = data.get("family_history", [])
    family_history_json = json.dumps(family_history if isinstance(family_history, list) else [])

    payload = {
        "full_name": data.get("full_name"),
        "phone_last4": data.get("phone_last4"),
        "age": data.get("age"),
        "gender": data.get("gender"),
        "height_cm": data.get("height_cm"),
        "weight_kg": data.get("weight_kg"),
        "family_history_json": family_history_json,
        "diabetes_type": data.get("diabetes_type"),
        "has_hypertension": data.get("has_hypertension"),
        "has_high_cholesterol": data.get("has_high_cholesterol"),
        "updated_at": now,
    }

    with get_engine().begin() as conn:
        exists = conn.execute(
            select(profiles.c.user_key).where(profiles.c.user_key == user_key)
        ).fetchone()

        if exists:
            conn.execute(
                update(profiles).where(profiles.c.user_key == user_key).values(**payload)
            )
        else:
            payload["user_key"] = user_key
            payload["created_at"] = now
            conn.execute(insert(profiles).values(**payload))

def add_glucose_log(user_key: str, measured_at: datetime, reading_type: str, value: float, meal_note: str = "") -> None:
    with get_engine().begin() as conn:
        conn.execute(insert(glucose_logs).values(
            user_key=user_key,
            measured_at=measured_at,
            logged_at=datetime.now(),
            reading_type=reading_type,
            value=float(value),
            meal_note=meal_note or None
        ))

def fetch_glucose_logs(user_key: str) -> List[Tuple[str, str, float, str]]:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(
                glucose_logs.c.measured_at,
                glucose_logs.c.reading_type,
                glucose_logs.c.value,
                glucose_logs.c.meal_note
            ).where(glucose_logs.c.user_key == user_key).order_by(glucose_logs.c.measured_at)
        ).fetchall()
    return [(r[0].isoformat(), r[1], float(r[2]), r[3] or "") for r in rows]

def add_daily_checkin(user_key: str, checkin_date: date, followed_plan: bool, actual_meals: str = "") -> None:
    with get_engine().begin() as conn:
        conn.execute(insert(daily_checkins).values(
            user_key=user_key,
            checkin_date=checkin_date,
            followed_plan=1 if followed_plan else 0,
            actual_meals=actual_meals or None,
            created_at=datetime.now()
        ))

def fetch_checkins(user_key: str) -> List[Tuple[str, int, str]]:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(
                daily_checkins.c.checkin_date,
                daily_checkins.c.followed_plan,
                daily_checkins.c.actual_meals
            ).where(daily_checkins.c.user_key == user_key).order_by(daily_checkins.c.checkin_date)
        ).fetchall()
    return [(r[0].isoformat(), int(r[1]), r[2] or "") for r in rows]
