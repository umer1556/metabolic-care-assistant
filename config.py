# config.py
# Prototype thresholds + settings (your doctor teammate can tweak these easily)

TRIAGE = {
    # Blood pressure routing (prototype triage)
    "bp_stage2_sys": 140,
    "bp_stage2_dia": 90,
    "bp_crisis_sys": 180,
    "bp_crisis_dia": 120,

    # Glucose (mg/dL) - typical reference ranges for awareness (not diagnosis)
    "hypo": 70,
    "premeal_high": 130,
    "postmeal_high": 180,
    "very_high": 300,

    # A1c (%) routing (prototype)
    "a1c_goal": 7.0,
    "a1c_caution": 8.0,
    "a1c_red": 9.0,

    # Total cholesterol (mg/dL) routing (prototype)
    "tc_borderline": 200,
    "tc_high": 240,

    # Stability / variation rules for recent fasting readings (prototype)
    # If user enters 2–3 fasting readings from recent days:
    "fasting_std_amber": 25.0,   # noticeable variability
    "fasting_std_red": 45.0,     # high variability
    "fasting_range_red": 120.0,  # large swings across days
}

CARB = {
    # 1 carb serving commonly treated as ~15g carbs (for awareness)
    "carb_serving_grams": 15
}

APP = {
    "title": "Metabolic Care Assistant (Prototype)",
    "disclaimer": (
        "Educational support tool only. Not medical advice. "
        "Does not diagnose, prescribe, or replace clinician care. "
        "If readings are concerning or you feel unwell, seek medical care."
    )
}
