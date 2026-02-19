# 🩺 Metabolic Care Assistant

> AI-powered dietary support and blood sugar tracking for people living with diabetes — built with real-world clinical safety in mind.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red) ![Groq](https://img.shields.io/badge/LLM-Groq%20%2F%20LLaMA%203.3-orange) ![Supabase](https://img.shields.io/badge/DB-Supabase%20PostgreSQL-green) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 🌍 The Problem

**Over 33 million Pakistanis live with diabetes** — the 3rd highest burden in the world. Millions more are undiagnosed. Yet access to personalised dietary guidance from clinicians is limited, expensive, and time-consuming.

Most people managing diabetes are left asking:
- *"Can I eat biryani?"*
- *"How much roti is too much?"*
- *"Is my blood sugar stable enough to change my habits?"*

Generic apps don't answer these questions in the context of desi food culture. Clinicians don't have time to give meal-by-meal guidance. **There's a gap — and this tool fills it.**

---

## 💡 What It Does

The **Metabolic Care Assistant** is a Generative AI-powered web app that:

1. **Triages users safely** — a clinical safety layer (GREEN / AMBER / RED) determines whether the user's blood sugar and BP readings are stable enough to use the tool independently, or whether they need to see a clinician first.
2. **Generates a personalised 7-day meal plan** — tailored to desi food preferences, vegetarian options, hypertension, and high cholesterol.
3. **Logs and visualises blood glucose readings** — with trend charts and stability insights.
4. **Tracks daily plan adherence** — and uses AI to coach users when they deviate from the plan.
5. **Suggests healthy food swaps** — using an LLM to provide safe, non-medical, practical alternatives.

---

## 🧠 Generative AI Integration

The app uses **Groq's API with LLaMA 3.3 70B** for two core AI features:

### 1. Healthy Swap Suggestions
When a user views their meal plan, they can request AI-generated alternatives. The LLM receives the day's meals and returns 3 culturally relevant, diabetes-safe swap ideas — no medication advice, no diagnosis, just practical food guidance.

```
User: "Day 3 plan includes nihari + naan"
AI: → "Try a smaller naan portion with added salad"
    → "Replace oil-heavy nihari gravy with a lighter shorba version"
    → "Add a side of raita (unsweetened) for protein without extra carbs"
```

### 2. Deviation Coaching
When a user logs that they didn't follow the plan and describes what they ate, the LLM gives 3 personalised tips on how to handle that food choice better next time — portion control, carb awareness, preparation methods.

Both AI calls are:
- Strictly non-diagnostic (enforced via prompt engineering)
- Gracefully fall back to sensible defaults if the API is unavailable
- Structured as JSON arrays for reliable parsing

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit Frontend                │
│  Login → 7-Day Plan → Profile → Check-in → Dashboard│
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼──────┐    ┌─────────▼────────┐
│  Groq / LLaMA│    │ Supabase Postgres│
│  3.3 70B     │    │  (via SQLAlchemy)│
│  - Swaps     │    │  - profiles      │
│  - Coaching  │    │  - glucose_logs  │
└──────────────┘    │  - daily_checkins│
                    └──────────────────┘
        │
┌───────▼──────────────────────────────┐
│           Core Python Modules        │
│  triage.py   — safety routing logic  │
│  planner.py  — meal plan generation  │
│  meal_bank.py— curated meal dataset  │
│  storage.py  — DB abstraction layer  │
│  llm.py      — Groq API integration  │
│  config.py   — thresholds & settings │
└──────────────────────────────────────┘
```

### Privacy by design
Phone numbers are **never stored**. A one-way SHA-256 hash (with a secret salt) is used as the user identifier. Even if the database was compromised, no phone numbers could be recovered.

---

## 🔐 Clinical Safety Layer (Triage)

Before the user accesses any features, the app evaluates:

| Signal | GREEN | AMBER | RED |
|---|---|---|---|
| HbA1c | < 8% | 8–9% | ≥ 9% |
| Fasting glucose variability | Low std dev | Std dev ≥ 25 | Std dev ≥ 45 or range ≥ 120 |
| Systolic BP | < 140 | 140–179 | ≥ 180 |
| Diastolic BP | < 90 | 90–119 | ≥ 120 |
| Total cholesterol | < 200 | 200–239 | — |
| Other major conditions | — | — | Immediate RED |

**RED users are blocked from all features** and directed to seek clinician care. This is a deliberate, non-negotiable safety decision.

---

## 🗂️ Project Structure

```
metabolic-care-assistant/
├── app.py           # Main Streamlit app — UI and flow
├── storage.py       # Database layer (SQLAlchemy + Supabase/SQLite)
├── triage.py        # Clinical safety routing logic
├── planner.py       # 7-day meal plan generation
├── meal_bank.py     # Curated meal dataset (desi + international)
├── llm.py           # Groq/LLaMA AI integration
├── config.py        # Thresholds, carb constants, app settings
├── requirements.txt # Python dependencies
└── .streamlit/
    └── secrets.toml # API keys (not committed — see setup below)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- A [Groq API key](https://console.groq.com) (free tier works)
- A [Supabase](https://supabase.com) project (free tier works) — or runs on local SQLite automatically

### 1. Clone the repo
```bash
git clone https://github.com/umer1556/metabolic-care-assistant.git
cd metabolic-care-assistant
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up secrets

Create `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY    = "your-groq-api-key"
DATABASE_URL    = "postgresql://..."   # from Supabase → Settings → Database → Connection string (Transaction pooler)
PHONE_SALT      = "any-random-secret-string"

# Optional — defaults shown
GROQ_BASE_URL   = "https://api.groq.com/openai/v1"
GROQ_MODEL      = "llama-3.3-70b-versatile"
```

> **No Supabase?** Leave `DATABASE_URL` empty — the app automatically falls back to a local `data.db` SQLite file.

### 4. Set up the database (Supabase only)

If using Supabase, run this in the SQL Editor to clear any old tables before first run:
```sql
DROP TABLE IF EXISTS daily_checkins;
DROP TABLE IF EXISTS glucose_logs;
DROP TABLE IF EXISTS profiles;
```
The app will recreate them correctly on startup.

### 5. Run the app
```bash
streamlit run app.py
```

---

## ☁️ Deploying to Streamlit Cloud

1. Push your code to GitHub (ensure `.streamlit/secrets.toml` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → select your repo
3. Add your secrets in the Streamlit Cloud dashboard under **Settings → Secrets**
4. Deploy

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `sqlalchemy>=2.0` | Database ORM |
| `psycopg[binary]` | PostgreSQL driver (psycopg3) |
| `openai>=1.0` | Groq API client (OpenAI-compatible) |
| `pandas` | Data handling for dashboard |
| `matplotlib` | Glucose trend charts |

---

## 🍽️ Meal Bank

The current meal bank contains **14 curated meals** across breakfast, lunch, dinner, and snacks — all tagged for dietary properties:

| Tag | Meaning |
|---|---|
| `desi` | South Asian dishes |
| `veg` | Vegetarian |
| `high_fiber` | Good for blood sugar stability |
| `low_sodium` | Suitable for hypertension |
| `low_satfat` | Suitable for high cholesterol |

The planner filters meals by these tags based on the user's conditions — e.g. a hypertensive user will only receive `low_sodium` meals where available.

> The meal bank is designed to be easily expanded. Each meal is a Python dict — a nutritionist or clinician can add entries without touching any app logic.

---

## ⚠️ Disclaimers & Limitations

- **Not a medical device.** This is an educational prototype built for a hackathon.
- **Not medication advice.** The app never suggests insulin doses, medication changes, or diagnostic conclusions.
- **Not a replacement for clinical care.** Users with RED triage results are explicitly blocked and directed to a clinician.
- The meal bank is small (14 meals) and should be reviewed and expanded by a registered dietitian before any real-world deployment.
- AI-generated suggestions are validated against a strict prompt but are not reviewed by a clinician in real time.

---

## 🔮 Future Roadmap

- [ ] Food photo analysis (multimodal) — snap a meal, get instant carb estimate
- [ ] Integration with glucose meters via Bluetooth / manual CSV import
- [ ] RAG over clinical dietary guidelines (e.g. ADA, IDF) for evidence-backed suggestions
- [ ] WhatsApp bot interface for low-tech users
- [ ] Dietitian review portal — flag high-risk users to a clinician dashboard
- [ ] Expanded meal bank with 100+ desi dishes, validated by a nutritionist

---

## 👥 Team

Built at the **HEC Generative AI Hackathon** by [umer1556](https://github.com/umer1556).

---

## 📄 License

MIT License — see `LICENSE` for details.
