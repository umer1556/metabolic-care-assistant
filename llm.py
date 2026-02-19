# llm.py
import json
import os
from typing import List
from openai import OpenAI


def _client():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _safe_fallback() -> List[str]:
    return [
        "Reduce rice/roti portion and add more salad/vegetables.",
        "Swap fried items for grilled, baked, or air-fried versions.",
        "Avoid sugary drinks; choose water or unsweetened tea.",
    ]


def generate_swaps(meal_text: str) -> List[str]:
    """Returns exactly 3 safe swap suggestions (no meds/dosing/diagnosis)."""
    client = _client()
    if client is None:
        return _safe_fallback()

    model  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = (
        "Return exactly 3 safe, non-medical 'healthy swap' suggestions for the meal below. "
        "No medication advice. No diagnosis. Keep it practical. "
        "Respond ONLY as a JSON array of 3 strings.\n\n"
        f"Meal: {meal_text}"
    )

    try:
        resp    = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = (resp.choices[0].message.content or "").strip()
        data    = json.loads(content)
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            return data[:3]
    except Exception:
        pass

    return _safe_fallback()


def coach_on_actual_meal(actual_meal_text: str) -> List[str]:
    """Friendly guidance if user deviated from plan."""
    client = _client()
    if client is None:
        return _safe_fallback()

    model  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = (
        "User ate the following foods instead of their plan. "
        "Give exactly 3 safe tips focused on portion control, carb awareness, and healthier preparation. "
        "No medication advice. No diagnosis. "
        "Respond ONLY as a JSON array of 3 strings.\n\n"
        f"Foods: {actual_meal_text}"
    )

    try:
        resp    = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = (resp.choices[0].message.content or "").strip()
        data    = json.loads(content)
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            return data[:3]
    except Exception:
        pass

    return _safe_fallback()
