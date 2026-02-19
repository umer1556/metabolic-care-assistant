# triage.py
from typing import List, Optional, Tuple
import math
from config import TRIAGE

def _mean(xs: List[float]) -> float:
    return sum(xs) / max(len(xs), 1)

def _std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)

def triage_profile(
    diabetes_type: str,
    has_hypertension: bool,
    has_high_cholesterol: bool,
    bp_sys: Optional[float],
    bp_dia: Optional[float],
    a1c: Optional[float],
    fasting_readings: List[float],
    total_cholesterol: Optional[float],
    other_major_conditions: bool,
) -> Tuple[str, List[str]]:
    """
    Returns:
      level: "GREEN" | "AMBER" | "RED"
      flags: list of human-readable notes
    """
    flags: List[str] = []
    level = "GREEN"

    # Hard stop
    if other_major_conditions:
        return "RED", ["Other major conditions selected → this prototype is not suitable. Please consult a clinician."]

    # Diabetes type is informational; do NOT change meds/doses, etc.
    if diabetes_type.strip().lower() == "type 1":
        flags.append("Type 1 selected → this tool is supportive only; do not use for medication decisions.")

    # BP logic only if they selected hypertension or provided BP values
    if has_hypertension or (bp_sys is not None and bp_dia is not None):
        if bp_sys is not None and bp_dia is not None:
            if bp_sys > TRIAGE["bp_crisis_sys"] or bp_dia > TRIAGE["bp_crisis_dia"]:
                return "RED", ["Blood pressure is in a severe range → seek urgent medical care."]
            if bp_sys >= TRIAGE["bp_stage2_sys"] or bp_dia >= TRIAGE["bp_stage2_dia"]:
                level = "AMBER"
                flags.append("Blood pressure is elevated (Stage 2 range) → clinician follow-up recommended.")
        else:
            flags.append("Hypertension selected but BP not provided → proceed with caution.")
            level = "AMBER"

    # Cholesterol logic only if selected or provided
    if has_high_cholesterol or (total_cholesterol is not None and total_cholesterol > 0):
        if total_cholesterol is not None and total_cholesterol > 0:
            if total_cholesterol >= TRIAGE["tc_high"]:
                level = "AMBER"
                flags.append("Total cholesterol is high → heart-healthy plan + clinician follow-up recommended.")
            elif total_cholesterol >= TRIAGE["tc_borderline"]:
                flags.append("Total cholesterol is borderline → heart-healthy plan recommended.")
        else:
            flags.append("High cholesterol selected but value not provided → proceed with caution.")
            level = "AMBER"

    # Glucose stability logic:
    # Use A1c if provided; otherwise use recent fasting readings (2–3 days)
    if a1c is not None and a1c > 0:
        if a1c >= TRIAGE["a1c_red"]:
            return "RED", ["HbA1c is very high → clinician review recommended before using an app-based plan."]
        if a1c >= TRIAGE["a1c_caution"]:
            level = "AMBER"
            flags.append("HbA1c above typical target → proceed with caution + clinician follow-up.")
        elif a1c > TRIAGE["a1c_goal"]:
            flags.append("HbA1c slightly above common target → focus on consistency and follow-up.")
    else:
        # Use fasting readings list if present
        fr = [x for x in fasting_readings if x is not None and x > 0]
        if len(fr) >= 1:
            # Red flags on extremes
            if any(x >= TRIAGE["very_high"] for x in fr):
                return "RED", ["Very high fasting glucose recorded → seek medical advice, especially if unwell."]
            if any(x < TRIAGE["hypo"] for x in fr):
                level = "AMBER"
                flags.append("Low fasting glucose detected → be cautious and discuss with clinician.")

            # Variability flags (2–3 days)
            if len(fr) >= 2:
                sd = _std(fr)
                rng = max(fr) - min(fr)
                if rng >= TRIAGE["fasting_range_red"] or sd >= TRIAGE["fasting_std_red"]:
                    return "RED", ["Large variation in recent fasting readings → clinician evaluation recommended."]
                if sd >= TRIAGE["fasting_std_amber"] or any(x > TRIAGE["premeal_high"] for x in fr):
                    level = "AMBER"
                    flags.append("Recent fasting readings show variability or are above typical range → proceed with caution.")
        else:
            # No A1c and no fasting readings
            flags.append("No A1c or recent fasting readings provided → proceed with caution.")
            level = "AMBER"

    return level, flags
