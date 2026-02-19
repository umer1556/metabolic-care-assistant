# storage.py
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple, Optional

DB_PATH = Path("data.db")

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS glucose_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        measured_at TEXT NOT NULL,
        logged_at TEXT NOT NULL,
        reading_type TEXT NOT NULL,
        value REAL NOT NULL,
        meal_note TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        checkin_date TEXT NOT NULL,
        followed_plan INTEGER NOT NULL,
        actual_meals TEXT,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def add_glucose_log(user: str, measured_at: datetime, reading_type: str, value: float, meal_note: str = "") -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO glucose_logs(user, measured_at, logged_at, reading_type, value, meal_note) VALUES(?,?,?,?,?,?)",
        (user, measured_at.isoformat(), datetime.now().isoformat(), reading_type, float(value), meal_note)
    )
    conn.commit()
    conn.close()

def fetch_glucose_logs(user: str) -> List[Tuple[str, str, float, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT measured_at, reading_type, value, COALESCE(meal_note,'') FROM glucose_logs WHERE user=? ORDER BY measured_at",
        (user,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def add_daily_checkin(user: str, checkin_date: date, followed_plan: bool, actual_meals: str = "") -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO daily_checkins(user, checkin_date, followed_plan, actual_meals, created_at) VALUES(?,?,?,?,?)",
        (user, checkin_date.isoformat(), 1 if followed_plan else 0, actual_meals, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def fetch_checkins(user: str) -> List[Tuple[str, int, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT checkin_date, followed_plan, COALESCE(actual_meals,'') FROM daily_checkins WHERE user=? ORDER BY checkin_date",
        (user,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
