# planner.py
import random
from typing import Dict, List
from meal_bank import MEALS

def _filter_meals(slot: str, prefer_desi: bool, veg_only: bool, needs_low_sodium: bool, needs_low_satfat: bool) -> List[Dict]:
    candidates = [m for m in MEALS if m["slot"] == slot]

    if veg_only:
        candidates = [m for m in candidates if "veg" in m.get("tags", []) or "desi" in m.get("tags", [])]  # simple rule

    if prefer_desi:
        desi = [m for m in candidates if "desi" in m.get("tags", [])]
        if desi:
            candidates = desi

    if needs_low_sodium:
        low = [m for m in candidates if "low_sodium" in m.get("tags", [])]
        if low:
            candidates = low

    if needs_low_satfat:
        low = [m for m in candidates if "low_satfat" in m.get("tags", [])]
        if low:
            candidates = low

    return candidates if candidates else [m for m in MEALS if m["slot"] == slot]

def generate_week_plan(
    prefer_desi: bool = True,
    veg_only: bool = False,
    has_hypertension: bool = False,
    has_high_cholesterol: bool = False,
) -> List[Dict]:
    week = []
    for day in range(1, 8):
        week.append({
            "day": day,
            "breakfast": random.choice(_filter_meals("breakfast", prefer_desi, veg_only, has_hypertension, has_high_cholesterol)),
            "lunch": random.choice(_filter_meals("lunch", prefer_desi, veg_only, has_hypertension, has_high_cholesterol)),
            "dinner": random.choice(_filter_meals("dinner", prefer_desi, veg_only, has_hypertension, has_high_cholesterol)),
            "snack": random.choice(_filter_meals("snack", prefer_desi, veg_only, False, False)),
        })
    return week
