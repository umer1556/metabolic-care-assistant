# app.py
import os
from datetime import datetime, date
from typing import List, Optional

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from config import APP, CARB, TRIAGE
from triage import triage_profile
from planner import generate_week_plan
from storage import (
    init_db,
    add_glucose_log,
    fetch_glucose_logs,
    add_daily_checkin,
    fetch_checkins,
)
from llm import generate_swaps, coach_on_actual_meal

st.set_page_config(page_title=APP["title"], layout="wide")

# Load Streamlit Secrets → environment variables (for Groq)
os.environ["GROQ_API_KEY"] = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
os.environ["GROQ_BASE_URL"] = st.secrets.get("GROQ_BASE_URL", os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
os.environ["GROQ_MODEL"] = st.secrets.get("GROQ_MODEL", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))

init_db()

st.title(APP["title"])
st.caption(APP["disclaimer"])

tabs = st.tabs(["1) Profile", "2) 7-Day Plan", "3) Daily Check-In", "4) Log Glucose", "5) Dashboard"])

# -------------------------
# Helpers
# -------------------------
def _get_user() -> str:
    return st.session_state.get("name", "").strip()

def _triage_level() -> Optional[str]:
    return st.session_state.get("triage_level")

def _blocked() -> bool:
    return _triage_level() == "RED"

def _parse_recent_fastings(vals: List[float]) -> List[float]:
    return [v for v in vals if v is not None and v > 0]

# -------------------------
# 1) Profile
# -------------------------
with tabs[0]:
    st.subheader("Create profile + eligibility (Green / Amber / Red)")

   name = st.text_input("Name", value=st.session_state.get("name", ""))
age = st.number_input("Age", min_value=1, max_value=120, value=int(st.session_state.get("age", 25)))

gender = st.selectbox(
    "Gender (optional)",
    ["Prefer not to say", "Male", "Female", "Other"],
    index=0
)

col_hw1, col_hw2 = st.columns(2)
with col_hw1:
    height_cm = st.number_input("Height (cm) (optional)", min_value=0, max_value=250, value=0)
with col_hw2:
    weight_kg = st.number_input("Weight (kg) (optional)", min_value=0.0, max_value=400.0, value=0.0, step=0.5)

family_history = st.multiselect(
    "Family history (optional)",
    ["Diabetes", "Hypertension", "High cholesterol", "Heart disease"],
    default=[]
)

diabetes_type = st.selectbox("Diabetes type", ["Type 1", "Type 2", "Not sure"], index=1)

# Optional BMI (informational only)
bmi = None
if height_cm > 0 and weight_kg > 0:
    h_m = height_cm / 100.0
    bmi = weight_kg / (h_m * h_m)
    st.caption(f"Estimated BMI (informational only): {bmi:.1f}")

    st.markdown("### Optional conditions")
    c1, c2, c3 = st.columns(3)
    with c1:
        has_hypertension = st.checkbox("I have hypertension / high blood pressure", value=st.session_state.get("has_hypertension", False))
    with c2:
        has_high_cholesterol = st.checkbox("I have high cholesterol", value=st.session_state.get("has_high_cholesterol", False))
    with c3:
        other_major = st.checkbox("Other major conditions (kidney disease, pregnancy, etc.)", value=False)

    st.markdown("### Your recent data (used to judge stability)")
    colA, colB, colC = st.columns(3)

    with colA:
        bp_sys = st.number_input("Systolic BP (optional)", min_value=0, max_value=300, value=130 if has_hypertension else 0)
        bp_dia = st.number_input("Diastolic BP (optional)", min_value=0, max_value=200, value=80 if has_hypertension else 0)

    with colB:
        a1c = st.number_input("HbA1c (%) — 3-month average (optional)", min_value=0.0, max_value=20.0, value=0.0, step=0.1)
        st.caption("If you don’t know A1c, enter 2–3 recent fasting readings below.")

    with colC:
        total_chol = st.number_input("Total cholesterol mg/dL (optional)", min_value=0.0, max_value=600.0, value=0.0, step=1.0)

    st.markdown("### Recent fasting readings (optional)")
    f1, f2, f3 = st.columns(3)
    with f1:
        fasting1 = st.number_input("Fasting (Day -3) mg/dL", min_value=0.0, max_value=600.0, value=0.0, step=1.0)
    with f2:
        fasting2 = st.number_input("Fasting (Day -2) mg/dL", min_value=0.0, max_value=600.0, value=0.0, step=1.0)
    with f3:
        fasting3 = st.number_input("Fasting (Day -1) mg/dL", min_value=0.0, max_value=600.0, value=0.0, step=1.0)

    if st.button("Save profile & run eligibility"):
        st.session_state["name"] = name
        st.session_state["age"] = age
        st.session_state["diabetes_type"] = diabetes_type
        st.session_state["has_hypertension"] = has_hypertension
        st.session_state["has_high_cholesterol"] = has_high_cholesterol
        st.session_state["gender"] = gender
        st.session_state["height_cm"] = height_cm
        st.session_state["weight_kg"] = weight_kg
        st.session_state["family_history"] = family_history
        st.session_state["bmi"] = bmi

        bp_sys_val = float(bp_sys) if bp_sys and bp_sys > 0 else None
        bp_dia_val = float(bp_dia) if bp_dia and bp_dia > 0 else None
        a1c_val = float(a1c) if a1c and a1c > 0 else None
        tc_val = float(total_chol) if total_chol and total_chol > 0 else None

        fasting_vals = _parse_recent_fastings([fasting1, fasting2, fasting3])

        level, flags = triage_profile(
            diabetes_type=diabetes_type,
            has_hypertension=has_hypertension,
            has_high_cholesterol=has_high_cholesterol,
            bp_sys=bp_sys_val,
            bp_dia=bp_dia_val,
            a1c=a1c_val,
            fasting_readings=fasting_vals,
            total_cholesterol=tc_val,
            other_major_conditions=other_major,
        )

        st.session_state["triage_level"] = level
        st.session_state["triage_flags"] = flags

    if "triage_level" in st.session_state:
        level = st.session_state["triage_level"]
        flags = st.session_state.get("triage_flags", [])

        if level == "GREEN":
            st.success("GREEN: Stable enough for the prototype flow.")
        elif level == "AMBER":
            st.warning("AMBER: You can proceed, but clinician follow-up is strongly recommended.")
        else:
            st.error("RED: This prototype is not suitable. Please seek clinician/hospital evaluation.")

        if flags:
            st.write("Notes:")
            for f in flags:
                st.write("•", f)
        # --- ADD THIS BELOW THE FLAGS ---
        if st.session_state.get("family_history"):
            st.info(
                f"Family history noted: {', '.join(st.session_state['family_history'])}. "
                "This tool supports habit-building; follow clinician guidance for targets."
            )

# -------------------------
# 2) 7-Day Plan
# -------------------------
with tabs[1]:
    st.subheader("7-Day diet plan (carb awareness + optional conditions)")

    if not _get_user():
        st.info("Create your profile first.")
    elif _blocked():
        st.info("Plan is disabled due to RED triage. Please seek clinician evaluation.")
    else:
        prefer_desi = st.toggle("Prefer Desi options", value=True)
        veg_only = st.toggle("Vegetarian only", value=False)

        if st.button("Generate / Regenerate plan"):
            st.session_state["week_plan"] = generate_week_plan(
                prefer_desi=prefer_desi,
                veg_only=veg_only,
                has_hypertension=st.session_state.get("has_hypertension", False),
                has_high_cholesterol=st.session_state.get("has_high_cholesterol", False),
            )

        plan = st.session_state.get("week_plan")

        if not plan:
            st.info("Click 'Generate / Regenerate plan' to create a plan.")
        else:
            for day in plan:
                with st.expander(f"Day {day['day']}"):
                    for slot in ["breakfast", "lunch", "dinner", "snack"]:
                        meal = day[slot]
                        carb_g = meal["carb_servings"] * CARB["carb_serving_grams"]
                        st.write(f"**{slot.title()}**: {meal['name']}")
                        st.caption(f"Carb estimate: ~{meal['carb_servings']} servings (≈ {carb_g}g carbs)")
                        st.write(f"Notes: {meal['notes']}")

                    if st.button(f"Healthy swaps (Day {day['day']})", key=f"swaps_{day['day']}"):
                        text = f"{day['breakfast']['name']}; {day['lunch']['name']}; {day['dinner']['name']}"
                        swaps = generate_swaps(text)
                        st.write("Swap suggestions:")
                        for s in swaps:
                            st.write("•", s)

# -------------------------
# 3) Daily Check-in
# -------------------------
with tabs[2]:
    st.subheader("Daily check-in (did you follow the plan?)")

    user = _get_user()
    if not user:
        st.info("Create your profile first.")
    elif _blocked():
        st.info("Daily check-in disabled due to RED triage. Please seek clinician evaluation.")
    else:
        checkin_date = st.date_input("Which day are you checking in for?", value=date.today())

        followed = st.radio("Did you follow the meal plan today?", ["Yes", "No"], horizontal=True)
        if followed == "Yes":
            if st.button("Save check-in"):
                add_daily_checkin(user, checkin_date, followed_plan=True, actual_meals="")
                st.success("Saved ✅ Great — consistency matters.")
        else:
            actual = st.text_area("What did you eat instead? (e.g., biryani, nihari, extra roti, sweets)", height=120)
            if st.button("Save check-in + get suggestions"):
                add_daily_checkin(user, checkin_date, followed_plan=False, actual_meals=actual.strip())
                st.success("Saved ✅ Here are safer ways to handle that choice next time:")
                profile_ctx = (
                f"Age: {st.session_state.get('age')}, "
                f"Gender: {st.session_state.get('gender')}, "
                f"Height_cm: {st.session_state.get('height_cm')}, "
                f"Weight_kg: {st.session_state.get('weight_kg')}, "
                f"BMI: {st.session_state.get('bmi')}, "
                f"FamilyHistory: {st.session_state.get('family_history')}"
                )

                tips = coach_on_actual_meal(f"{actual.strip()} | Profile: {profile_ctx}")

                for t in tips:
                    st.write("•", t)

# -------------------------
# 4) Log Glucose
# -------------------------
with tabs[3]:
    st.subheader("Log blood sugar (measured time vs logged time)")

    user = _get_user()
    if not user:
        st.info("Create your profile first.")
    elif _blocked():
        st.info("Logging is disabled due to RED triage. Please seek clinician evaluation.")
    else:
        reading_type = st.selectbox("Reading type", ["Fasting", "Pre-meal", "Post-meal (1–2h)", "Bedtime"])
        measured_at = st.datetime_input("When did you measure it?", value=datetime.now())
        value = st.number_input("Glucose (mg/dL)", min_value=0.0, max_value=600.0, value=110.0, step=1.0)
        meal_note = st.text_input("Meal note (optional)", placeholder="e.g., biryani, nihari, roti, sweets…")

        if st.button("Save reading"):
            add_glucose_log(user, measured_at, reading_type, value, meal_note)
            st.success("Saved ✅")

        st.caption(f"Safety hints: low < {TRIAGE['hypo']} • very high ≥ {TRIAGE['very_high']} (mg/dL)")

# -------------------------
# 5) Dashboard
# -------------------------
with tabs[4]:
    st.subheader("Weekly summary (non-diagnostic)")

    user = _get_user()
    if not user:
        st.info("Create your profile first.")
    else:
        # Check-ins summary
        checkins = fetch_checkins(user)
        if checkins:
            cdf = pd.DataFrame(checkins, columns=["date", "followed_plan", "actual_meals"])
            cdf["date"] = pd.to_datetime(cdf["date"]).dt.date
            adherence = (cdf["followed_plan"].sum() / len(cdf)) * 100.0
            st.write(f"**Adherence:** {adherence:.0f}% ({int(cdf['followed_plan'].sum())}/{len(cdf)} days)")
            st.dataframe(cdf, use_container_width=True)
        else:
            st.info("No daily check-ins yet.")

        # Glucose summary
        rows = fetch_glucose_logs(user)
        if not rows:
            st.info("No glucose logs yet.")
        else:
            df = pd.DataFrame(rows, columns=["measured_at", "type", "value", "meal_note"])
            df["measured_at"] = pd.to_datetime(df["measured_at"])
            st.dataframe(df, use_container_width=True)

            st.write("### Trend")
            fig = plt.figure()
            plt.plot(df["measured_at"], df["value"])
            plt.xticks(rotation=30)
            st.pyplot(fig)

            st.write("### Quick insights")
            st.write(f"- Average: **{df['value'].mean():.1f} mg/dL**")
            st.write(f"- Variability (std dev): **{df['value'].std():.1f}**")

            high = (df["value"] >= TRIAGE["very_high"]).sum()
            low = (df["value"] < TRIAGE["hypo"]).sum()
            if high:
                st.warning("Very high readings detected. If you feel unwell or readings stay high, seek medical care.")
            if low:
                st.warning("Low readings detected. Treat low glucose promptly and discuss with your clinician.")
