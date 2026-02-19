import os
import re
import hashlib
from datetime import datetime, date, time
from typing import List, Optional

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from config import APP, CARB, TRIAGE
from triage import triage_profile
from planner import generate_week_plan
from llm import generate_swaps, coach_on_actual_meal

st.set_page_config(page_title=APP["title"], layout="wide", page_icon="🩺")

# ---- Load secrets FIRST ----
def _sget(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(key, default)).strip()
    except Exception:
        return default

os.environ["GROQ_API_KEY"]   = _sget("GROQ_API_KEY",   os.getenv("GROQ_API_KEY", ""))
os.environ["GROQ_BASE_URL"]  = _sget("GROQ_BASE_URL",  os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
os.environ["GROQ_MODEL"]     = _sget("GROQ_MODEL",     os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
os.environ["DATABASE_URL"]   = _sget("DATABASE_URL",   os.getenv("DATABASE_URL", ""))
os.environ["PHONE_SALT"]     = _sget("PHONE_SALT",     os.getenv("PHONE_SALT", "dev-salt-change-me"))

from storage import (
    init_db, get_profile, upsert_profile,
    add_glucose_log, fetch_glucose_logs,
    add_daily_checkin, fetch_checkins,
)

init_db()

# -------------------------
# Helpers
# -------------------------
def normalize_phone(phone: str) -> str:
    phone = phone.strip()
    return re.sub(r"[^\d+]", "", phone)

def user_key_from_phone(phone: str) -> str:
    salt = os.getenv("PHONE_SALT", "dev-salt-change-me")
    return hashlib.sha256((salt + phone).encode("utf-8")).hexdigest()

def last4(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return digits[-4:] if len(digits) >= 4 else digits

def _get_user() -> str:
    return st.session_state.get("user_key", "").strip()

def _triage_level() -> Optional[str]:
    return st.session_state.get("triage_level")

def _blocked() -> bool:
    return _triage_level() == "RED"

def _parse_recent_fastings(vals: List[float]) -> List[float]:
    return [v for v in vals if v is not None and v > 0]

TRIAGE_EMOJI = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}

# -------------------------
# Sidebar
# -------------------------
def _render_sidebar():
    st.sidebar.title("🩺 " + APP["title"])

    if _get_user():
        st.sidebar.success(f"👤 {st.session_state.get('display_name', 'User')}")

        level = _triage_level()
        if level:
            emoji = TRIAGE_EMOJI.get(level, "")
            label = {
                "GREEN": "Stable — proceed with plan",
                "AMBER": "Proceed with caution",
                "RED":   "Seek clinician evaluation",
            }.get(level, "")
            st.sidebar.markdown(f"**Eligibility:** {emoji} {level}  \n_{label}_")

        st.sidebar.divider()
        if st.sidebar.button("🚪 Logout"):
            st.session_state["_confirm_logout"] = True

        if st.session_state.get("_confirm_logout"):
            st.sidebar.warning("Are you sure?")
            c1, c2 = st.sidebar.columns(2)
            if c1.button("Yes"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
            if c2.button("No"):
                st.session_state["_confirm_logout"] = False
                st.rerun()

    st.sidebar.divider()
    with st.sidebar.expander("⚠️ Medical Disclaimer", expanded=False):
        st.markdown(
            """
**For general informational purposes only — not a substitute for medical advice.**

- Not medication dosing advice
- If glucose is repeatedly above **180 mg/dL**, consult your doctor
- **Hypo signs:** shakiness, sweating, dizziness, confusion → seek help
- **Hyper signs:** frequent urination, excessive thirst, blurred vision → consult doctor
- Always follow your healthcare provider's instructions
            """
        )

_render_sidebar()

# -------------------------
# Login screen
# -------------------------
if "user_key" not in st.session_state:
    st.title("🩺 " + APP["title"])
    st.markdown("#### Your personal metabolic health companion.")
    st.caption("🔒 Private & secure — your phone number is never stored.")

    col1, col2 = st.columns([1, 1])
    with col1:
        full_name = st.text_input("Full Name")
        phone = st.text_input("Phone Number", placeholder="+92xxxxxxxxxx or +44xxxxxxxxxx")
        st.caption("Include country code e.g. +92, +44, +1")

        if st.button("Continue →", type="primary", use_container_width=True):
            phone_n = normalize_phone(phone)

            if not full_name.strip():
                st.error("Please enter your full name.")
                st.stop()
            if not phone_n.startswith("+") or len(phone_n) < 8:
                st.error("Please enter a valid phone number with country code e.g. +92...")
                st.stop()

            with st.spinner("Logging in..."):
                user_key = user_key_from_phone(phone_n)
                st.session_state["user_key"]      = user_key
                st.session_state["display_name"]  = full_name.strip()
                st.session_state["phone_last4"]   = last4(phone_n)

                prof = get_profile(user_key)
                if prof:
                    st.session_state["name"]               = prof.get("full_name") or full_name.strip()
                    st.session_state["age"]                = prof.get("age") or 25
                    st.session_state["gender"]             = prof.get("gender") or "Prefer not to say"
                    st.session_state["height_cm"]          = prof.get("height_cm") or 0
                    st.session_state["weight_kg"]          = prof.get("weight_kg") or 0.0
                    st.session_state["family_history"]     = prof.get("family_history") or []
                    st.session_state["diabetes_type"]      = prof.get("diabetes_type") or "Type 2"
                    st.session_state["has_hypertension"]   = bool(prof.get("has_hypertension") or 0)
                    st.session_state["has_high_cholesterol"] = bool(prof.get("has_high_cholesterol") or 0)
                    st.session_state["phone_last4"]        = prof.get("phone_last4") or st.session_state.get("phone_last4")
                    st.success(f"Welcome back, {st.session_state['name']}!")
                else:
                    upsert_profile(user_key, {
                        "full_name":   full_name.strip(),
                        "phone_last4": st.session_state.get("phone_last4"),
                        "family_history": [],
                    })
                    st.success(f"Welcome, {full_name.strip()}! Let's set up your profile.")

            st.rerun()

    with col2:
        st.markdown("""
        **What this app does:**
        - 🥗 Creates a personalised 7-day meal plan
        - 📊 Tracks your blood sugar readings
        - ✅ Logs your daily meal plan adherence
        - 💡 Gives AI-powered healthy food swaps

        **Privacy:** Your phone number is never stored — only a one-way hash is used to identify you.
        """)

    st.stop()

# -------------------------
# Main app tabs
# -------------------------
tabs = st.tabs([
    "🥗 Meal Plan",
    "👤 My Profile",
    "✅ Daily Check-In",
    "📊 Log Glucose",
    "📈 Dashboard",
])

# -------------------------
# TAB 0 — 7-Day Plan (shown FIRST for immediate value)
# -------------------------
with tabs[0]:
    st.subheader("🥗 Your 7-Day Meal Plan")

    if _blocked():
        st.error("🔴 Plan is disabled — your triage result is RED. Please seek clinician evaluation before using this tool.")
    else:
        if _triage_level() is None:
            st.info("💡 **Tip:** Complete your profile (tab 2) to get a personalised plan. For now, here's a default plan — fill in your details to tailor it to your conditions.")

        col1, col2 = st.columns([1, 1])
        with col1:
            prefer_desi = st.toggle("🍛 Prefer Desi options", value=st.session_state.get("prefer_desi", True))
        with col2:
            veg_only = st.toggle("🥦 Vegetarian only", value=st.session_state.get("veg_only", False))

        st.session_state["prefer_desi"] = prefer_desi
        st.session_state["veg_only"]    = veg_only

        if st.button("🔄 Generate / Regenerate Plan", type="primary"):
            with st.spinner("Building your 7-day plan..."):
                st.session_state["week_plan"] = generate_week_plan(
                    prefer_desi=prefer_desi,
                    veg_only=veg_only,
                    has_hypertension=st.session_state.get("has_hypertension", False),
                    has_high_cholesterol=st.session_state.get("has_high_cholesterol", False),
                )

        # Auto-generate if no plan yet
        if not st.session_state.get("week_plan"):
            with st.spinner("Loading your default plan..."):
                st.session_state["week_plan"] = generate_week_plan(
                    prefer_desi=prefer_desi,
                    veg_only=veg_only,
                    has_hypertension=st.session_state.get("has_hypertension", False),
                    has_high_cholesterol=st.session_state.get("has_high_cholesterol", False),
                )

        plan = st.session_state.get("week_plan", [])
        if plan:
            for day in plan:
                day_carbs = sum(
                    day[slot]["carb_servings"] * CARB["carb_serving_grams"]
                    for slot in ["breakfast", "lunch", "dinner", "snack"]
                )
                with st.expander(f"📅 Day {day['day']}  —  ~{day_carbs:.0f}g carbs total"):
                    for slot in ["breakfast", "lunch", "dinner", "snack"]:
                        meal = day[slot]
                        carb_g = meal["carb_servings"] * CARB["carb_serving_grams"]
                        icon = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙", "snack": "🍎"}.get(slot, "🍽️")
                        st.markdown(f"**{icon} {slot.title()}:** {meal['name']}")
                        st.caption(f"~{meal['carb_servings']} carb servings ≈ {carb_g}g carbs  |  {meal['notes']}")

                    if st.button(f"💡 Suggest healthy swaps", key=f"swaps_{day['day']}"):
                        with st.spinner("Getting swap suggestions..."):
                            text = f"{day['breakfast']['name']}; {day['lunch']['name']}; {day['dinner']['name']}"
                            swaps = generate_swaps(text)
                        st.markdown("**Swap suggestions:**")
                        for s in swaps:
                            st.write("•", s)

# -------------------------
# TAB 1 — Profile & Eligibility
# -------------------------
with tabs[1]:
    st.subheader("👤 Profile & Eligibility Check")
    st.caption("Complete this once to personalise your plan and check if this tool is right for you.")

    # --- Basic info ---
    st.markdown("### Basic information")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name", value=st.session_state.get("name", ""))
        age  = st.number_input("Age", min_value=1, max_value=120, value=int(st.session_state.get("age", 25)))
    with col2:
        gender_options = ["Prefer not to say", "Male", "Female", "Other"]
        saved_gender   = st.session_state.get("gender", "Prefer not to say")
        gender_index   = gender_options.index(saved_gender) if saved_gender in gender_options else 0
        gender = st.selectbox("Gender (optional)", gender_options, index=gender_index)

        diabetes_type_options = ["Type 1", "Type 2", "Not sure"]
        saved_dtype = st.session_state.get("diabetes_type", "Type 2")
        dtype_index = diabetes_type_options.index(saved_dtype) if saved_dtype in diabetes_type_options else 1
        diabetes_type = st.selectbox("Diabetes type", diabetes_type_options, index=dtype_index)

    col_h, col_w = st.columns(2)
    with col_h:
        height_cm = st.number_input("Height (cm)", min_value=0, max_value=250,
                                     value=int(st.session_state.get("height_cm", 0) or 0))
    with col_w:
        weight_kg = st.number_input("Weight (kg)", min_value=0.0, max_value=400.0,
                                     value=float(st.session_state.get("weight_kg", 0.0) or 0.0), step=0.5)

    bmi = None
    if height_cm > 0 and weight_kg > 0:
        bmi = weight_kg / ((height_cm / 100.0) ** 2)
        st.caption(f"Estimated BMI: **{bmi:.1f}** (informational only)")

    family_history = st.multiselect(
        "Family history (optional)",
        ["Diabetes", "Hypertension", "High cholesterol", "Heart disease"],
        default=st.session_state.get("family_history", [])
    )

    # --- Conditions ---
    st.markdown("### Conditions")
    c1, c2, c3 = st.columns(3)
    with c1:
        has_hypertension     = st.checkbox("I have hypertension / high blood pressure",
                                            value=st.session_state.get("has_hypertension", False))
    with c2:
        has_high_cholesterol = st.checkbox("I have high cholesterol",
                                            value=st.session_state.get("has_high_cholesterol", False))
    with c3:
        other_major          = st.checkbox("Other major conditions (kidney disease, pregnancy, etc.)")

    # --- Advanced health data (optional) ---
    with st.expander("🔬 Advanced health data (optional — helps eligibility check)", expanded=False):
        st.caption("Fill in what you know. Leave as 0 if unsure.")

        colA, colB, colC = st.columns(3)
        with colA:
            bp_sys = st.number_input("Systolic BP (mmHg)",  min_value=0, max_value=300,
                                      value=130 if has_hypertension else 0,
                                      help="The top number in a blood pressure reading e.g. 130 in 130/80")
            bp_dia = st.number_input("Diastolic BP (mmHg)", min_value=0, max_value=200,
                                      value=80 if has_hypertension else 0,
                                      help="The bottom number in a blood pressure reading e.g. 80 in 130/80")
        with colB:
            a1c = st.number_input("HbA1c (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.1,
                                   help="Your 3-month average blood sugar from a lab test. Usually between 5–10%.")
        with colC:
            total_chol = st.number_input("Total cholesterol (mg/dL)", min_value=0.0, max_value=600.0,
                                          value=0.0, step=1.0,
                                          help="From a lipid panel blood test. Normal is under 200 mg/dL.")

        st.markdown("**Recent fasting glucose readings** (if you don't know your HbA1c)",
                    help="Fasting = no food for 8+ hours before measuring")
        f1, f2, f3 = st.columns(3)
        with f1:
            fasting1 = st.number_input("Day -3 (mg/dL)", min_value=0.0, max_value=600.0, value=0.0, step=1.0)
        with f2:
            fasting2 = st.number_input("Day -2 (mg/dL)", min_value=0.0, max_value=600.0, value=0.0, step=1.0)
        with f3:
            fasting3 = st.number_input("Day -1 (mg/dL)", min_value=0.0, max_value=600.0, value=0.0, step=1.0)

    if st.button("💾 Save profile & check eligibility", type="primary"):
        with st.spinner("Saving and running eligibility check..."):
            st.session_state.update({
                "name": name.strip(), "age": int(age), "diabetes_type": diabetes_type,
                "has_hypertension": has_hypertension, "has_high_cholesterol": has_high_cholesterol,
                "gender": gender, "height_cm": int(height_cm),
                "weight_kg": float(weight_kg), "family_history": family_history, "bmi": bmi,
            })

            bp_sys_val = float(bp_sys) if bp_sys and bp_sys > 0 else None
            bp_dia_val = float(bp_dia) if bp_dia and bp_dia > 0 else None
            a1c_val    = float(a1c)    if a1c    and a1c    > 0 else None
            tc_val     = float(total_chol) if total_chol and total_chol > 0 else None
            fasting_vals = _parse_recent_fastings([fasting1, fasting2, fasting3])

            level, flags = triage_profile(
                diabetes_type=diabetes_type,
                has_hypertension=has_hypertension,
                has_high_cholesterol=has_high_cholesterol,
                bp_sys=bp_sys_val, bp_dia=bp_dia_val,
                a1c=a1c_val, fasting_readings=fasting_vals,
                total_cholesterol=tc_val,
                other_major_conditions=other_major,
            )
            st.session_state["triage_level"] = level
            st.session_state["triage_flags"] = flags

            upsert_profile(st.session_state["user_key"], {
                "full_name":            name.strip(),
                "phone_last4":          st.session_state.get("phone_last4"),
                "age":                  int(age) if age else None,
                "gender":               gender,
                "height_cm":            int(height_cm) if height_cm else None,
                "weight_kg":            float(weight_kg) if weight_kg else None,
                "family_history":       family_history,
                "diabetes_type":        diabetes_type,
                "has_hypertension":     1 if has_hypertension else 0,
                "has_high_cholesterol": 1 if has_high_cholesterol else 0,
            })

            # Regenerate plan with updated conditions
            st.session_state["week_plan"] = generate_week_plan(
                prefer_desi=st.session_state.get("prefer_desi", True),
                veg_only=st.session_state.get("veg_only", False),
                has_hypertension=has_hypertension,
                has_high_cholesterol=has_high_cholesterol,
            )

        st.success("✅ Profile saved! Your plan has been updated.")

    if "triage_level" in st.session_state:
        level = st.session_state["triage_level"]
        flags = st.session_state.get("triage_flags", [])
        emoji = TRIAGE_EMOJI.get(level, "")

        if level == "GREEN":
            st.success(f"{emoji} **All clear** — Your readings look stable. All features are unlocked.")
       elif level == "AMBER":
            st.warning(f"{emoji} **Proceed with care** — You can use the app, but we strongly recommend discussing your plan with a clinician.")
       else:
            st.error(f"{emoji} **Please see a clinician** — Your current readings suggest this app alone isn't enough. Please seek professional medical advice before making dietary changes.")

        if flags:
            for f in flags:
                st.write("•", f)

        if family_history:
            st.info(f"📋 Family history noted: {', '.join(family_history)}. This tool supports habit-building; follow clinician guidance for specific targets.")

# -------------------------
# TAB 2 — Daily Check-In
# -------------------------
with tabs[2]:
    st.subheader("✅ Daily Check-In")

    user = _get_user()
    if not user:
        st.info("Please log in first.")
    elif _blocked():
        st.error("🔴 Daily check-in disabled — please seek clinician evaluation.")
    else:
        checkin_date = st.date_input("Which day are you checking in for?", value=date.today())
        followed     = st.radio("Did you follow the meal plan today?", ["Yes", "No"], horizontal=True)

        if followed == "Yes":
            if st.button("💾 Save check-in", type="primary"):
                with st.spinner("Saving..."):
                    add_daily_checkin(user, checkin_date, followed_plan=True, actual_meals="")
                st.success("✅ Saved! Great work — consistency is what matters most.")
                st.balloons()
        else:
            actual = st.text_area(
                "What did you eat instead?",
                placeholder="e.g., biryani, nihari, extra roti, sweets, fried snacks...",
                height=100
            )
            if st.button("💾 Save + get suggestions", type="primary"):
                if not actual.strip():
                    st.warning("Please describe what you ate to get suggestions.")
                else:
                    with st.spinner("Saving and getting personalised tips..."):
                        add_daily_checkin(user, checkin_date, followed_plan=False, actual_meals=actual.strip())
                        profile_ctx = (
                            f"Age: {st.session_state.get('age')}, "
                            f"Gender: {st.session_state.get('gender')}, "
                            f"BMI: {st.session_state.get('bmi')}, "
                            f"FamilyHistory: {st.session_state.get('family_history')}"
                        )
                        tips = coach_on_actual_meal(f"{actual.strip()} | Profile: {profile_ctx}")

                    st.success("✅ Saved! Here are safer ways to handle that choice next time:")
                    for t in tips:
                        st.write("•", t)

# -------------------------
# TAB 3 — Log Glucose
# -------------------------
with tabs[3]:
    st.subheader("📊 Log Blood Sugar Reading")

    user = _get_user()
    if not user:
        st.info("Please log in first.")
    elif _blocked():
        st.error("🔴 Logging disabled — please seek clinician evaluation.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            reading_type = st.selectbox(
                "Reading type",
                ["Fasting", "Pre-meal", "Post-meal (1–2h)", "Bedtime"],
                help="Fasting = no food for 8+ hours. Post-meal = 1–2 hours after eating."
            )
            measure_date = st.date_input("Date of measurement", value=date.today())
            measure_time = st.time_input("Time of measurement", value=datetime.now().time())
        with col2:
            value     = st.number_input("Glucose reading (mg/dL)", min_value=0.0, max_value=600.0, value=110.0, step=1.0)
            meal_note = st.text_input("Meal note (optional)", placeholder="e.g., biryani, nihari, roti...")

            st.caption(
                f"Reference: 🟡 Low < {TRIAGE['hypo']} mg/dL  |  "
                f"🟢 Fasting target 80–130  |  "
                f"🔴 Very high ≥ {TRIAGE['very_high']} mg/dL"
            )

            if value >= TRIAGE["very_high"]:
                st.error("⚠️ This reading is very high. If you feel unwell, seek medical care.")
            elif value < TRIAGE["hypo"]:
                st.warning("⚠️ This reading is low. Treat hypoglycaemia promptly and consult your clinician.")

        if st.button("💾 Save reading", type="primary"):
            measured_at = datetime.combine(measure_date, measure_time)
            with st.spinner("Saving..."):
                add_glucose_log(user, measured_at, reading_type, value, meal_note)
            st.success("✅ Reading saved!")

# -------------------------
# TAB 4 — Dashboard
# -------------------------
with tabs[4]:
    st.subheader("📈 Weekly Summary")
    st.caption("For awareness and habit tracking only — not a diagnostic tool.")

    user = _get_user()
    if not user:
        st.info("Please log in first.")
    else:
        col1, col2 = st.columns(2)

        # Check-ins
        with col1:
            st.markdown("### 📅 Plan adherence")
            checkins = fetch_checkins(user)
            if checkins:
                cdf = pd.DataFrame(checkins, columns=["date", "followed_plan", "actual_meals"])
                cdf["date"] = pd.to_datetime(cdf["date"]).dt.date
                adherence = (cdf["followed_plan"].sum() / len(cdf)) * 100.0
                st.metric("Adherence rate", f"{adherence:.0f}%",
                           delta=f"{int(cdf['followed_plan'].sum())} of {len(cdf)} days")
                st.dataframe(cdf[["date", "followed_plan"]].rename(
                    columns={"followed_plan": "Followed plan?"}), use_container_width=True)
            else:
                st.info("📋 No check-ins yet. Use the **Daily Check-In** tab to start tracking.")

        # Glucose
        with col2:
            st.markdown("### 🩸 Glucose readings")
            rows = fetch_glucose_logs(user)
            if rows:
                df = pd.DataFrame(rows, columns=["measured_at", "type", "value", "meal_note"])
                df["measured_at"] = pd.to_datetime(df["measured_at"])

                avg = df["value"].mean()
                std = df["value"].std()
                high_count = (df["value"] >= TRIAGE["very_high"]).sum()
                low_count  = (df["value"] < TRIAGE["hypo"]).sum()

                m1, m2, m3 = st.columns(3)
                m1.metric("Average", f"{avg:.0f} mg/dL")
                m2.metric("Variability", f"±{std:.0f}")
                m3.metric("Total logs", len(df))

                if high_count:
                    st.warning(f"⚠️ {high_count} very high reading(s). If persistent or you feel unwell, see your doctor.")
                if low_count:
                    st.warning(f"⚠️ {low_count} low reading(s). Discuss with your clinician.")
            else:
                st.info("🩸 No glucose readings yet. Use the **Log Glucose** tab to start tracking.")

        # Full glucose chart (below columns)
        if rows:
            st.markdown("### Trend")
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot(df["measured_at"], df["value"], marker="o", linewidth=1.5, color="#e05c5c")
            ax.axhline(TRIAGE["very_high"], color="red",    linestyle="--", alpha=0.5, label=f"Very high ({TRIAGE['very_high']})")
            ax.axhline(TRIAGE["hypo"],      color="orange", linestyle="--", alpha=0.5, label=f"Low ({TRIAGE['hypo']})")
            ax.set_ylabel("mg/dL")
            ax.legend(fontsize=8)
            plt.xticks(rotation=30)
            plt.tight_layout()
            st.pyplot(fig)

            with st.expander("View all readings"):
                st.dataframe(df.rename(columns={
                    "measured_at": "Time", "type": "Type",
                    "value": "mg/dL", "meal_note": "Meal note"
                }), use_container_width=True)
