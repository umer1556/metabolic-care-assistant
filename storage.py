# storage.py
import os
from datetime import datetime, date
from typing import List, Tuple

from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, Float, String, Date, DateTime, Text
)
from sqlalchemy.sql import select, insert

DB_URL = os.getenv("DATABASE_URL", "").strip()

# If DATABASE_URL exists -> persistent Postgres. Otherwise -> local SQLite (for local dev).
if DB_URL:
    engine = create_engine(DB_URL, pool_pre_ping=True)
else:
    engine = create_engine("sqlite:///data.db", connect_args={"check_same_thread": False})

metadata = MetaData()

glucose_logs = Table(
    "glucose_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user", String(120), nullable=False),
    Column("measured_at", DateTime, nullable=False),
    Column("logged_at", DateTime, nullable=False),
    Column("reading_type", String(40), nullable=False),
    Column("value", Float, nullable=False),
    Column("meal_note", Text, nullable=True),
)

daily_checkins = Table(
    "daily_checkins", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user", String(120), nullable=False),
    Column("checkin_date", Date, nullable=False),
    Column("followed_plan", Integer, nullable=False),  # 1 or 0
    Column("actual_meals", Text, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

def init_db() -> None:
    metadata.create_all(engine)

def add_glucose_log(user: str, measured_at: datetime, reading_type: str, value: float, meal_note: str = "") -> None:
    with engine.begin() as conn:
        conn.execute(insert(glucose_logs).values(
            user=user,
            measured_at=measured_at,
            logged_at=datetime.now(),
            reading_type=reading_type,
            value=float(value),
            meal_note=meal_note or None
        ))

def fetch_glucose_logs(user: str) -> List[Tuple[str, str, float, str]]:
    with engine.begin() as conn:
        rows = conn.execute(
            select(
                glucose_logs.c.measured_at,
                glucose_logs.c.reading_type,
                glucose_logs.c.value,
                glucose_logs.c.meal_note
            ).where(glucose_logs.c.user == user).order_by(glucose_logs.c.measured_at)
        ).fetchall()

    # Normalize output to match your app expectations
    return [(r[0].isoformat(), r[1], float(r[2]), r[3] or "") for r in rows]

def add_daily_checkin(user: str, checkin_date: date, followed_plan: bool, actual_meals: str = "") -> None:
    with engine.begin() as conn:
        conn.execute(insert(daily_checkins).values(
            user=user,
            checkin_date=checkin_date,
            followed_plan=1 if followed_plan else 0,
            actual_meals=actual_meals or None,
            created_at=datetime.now()
        ))

def fetch_checkins(user: str) -> List[Tuple[str, int, str]]:
    with engine.begin() as conn:
        rows = conn.execute(
            select(
                daily_checkins.c.checkin_date,
                daily_checkins.c.followed_plan,
                daily_checkins.c.actual_meals
            ).where(daily_checkins.c.user == user).order_by(daily_checkins.c.checkin_date)
        ).fetchall()

    return [(r[0].isoformat(), int(r[1]), r[2] or "") for r in rows]
