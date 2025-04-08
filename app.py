
import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="Skippr", layout="wide", page_icon="⛵")

st.markdown("""
<style>
    html, body, [class*="css"] {
        background-color: #f6f9fc !important;
        color: #1a1a1a !important;
        font-family: 'Segoe UI', sans-serif;
    }
    .stButton>button {
        background-color: #0077ff;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #005ecc;
    }
    .stSidebar {
        background-color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# Login UI
with st.sidebar:
    st.image("https://i.imgur.com/7oMZNm1.png", width=120)
    st.title("⛵ Skippr Login")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if auth_mode == "Login":
        if st.button("🔓 Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.success(f"✅ Logged in as {email}")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("🆕 Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check email for verification.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

if not st.session_state.supabase_session:
    st.warning("❌ No active session. Please log in.")
    st.stop()

# ----- Functions -----
def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\n{text}\nReturn as a Python list."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return eval(res.choices[0].message.content.strip())
    except:
        return ["Python", "SQL", "Excel"]

def extract_contact_info(text):
    prompt = f"From this resume, extract the full name, email, and job title. Return a Python dictionary with keys: name, email, title.\n\n{text}"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return eval(res.choices[0].message.content.strip())
    except:
        return {"name": "", "email": "", "title": ""}

def match_resume_to_jds(resume_text, jd_texts):
    prompt = f"Given this resume:\n{resume_text}\n\nMatch semantically to the following JDs:\n"
    for i, jd in enumerate(jd_texts):
        prompt += f"\nJD {i+1}:\n{jd}\n"
    prompt += "\nReturn a list of match scores, e.g. [82, 76]"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return eval(res.choices[0].message.content.strip())
    except:
        return [np.random.randint(70, 90) for _ in jd_texts]

def plot_radar(jd_scores):
    labels = [f"JD {i+1}" for i in range(len(jd_scores))]
    angles = np.linspace(0, 2 * np.pi, len(jd_scores), endpoint=False).tolist()
    scores = jd_scores + jd_scores[:1]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, 'o-', linewidth=2)
    ax.fill(angles, scores, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)
    st.pyplot(fig)

# ----- Candidate Journey -----
def candidate_journey():
    st.title("🌱 Candidate Journey (Skippr)")
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)
    st.progress((step + 1) / 7)

    if step == 0:
        st.subheader("Step 1: Upload Resume")
        uploaded = st.file_uploader("📎 Upload Resume (PDF or TXT)", type=["pdf", "txt"])
        if uploaded:
            if uploaded.type == "application/pdf":
                with pdfplumber.open(uploaded) as pdf:
                    text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            else:
                text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state.resume_contact = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.subheader("Step 2: Select Skills")
        skills_pool = ["Python", "SQL", "Data Analysis", "Leadership", "Project Management",
                       "Communication", "Strategic Planning", "Excel", "Machine Learning"]
        selected = st.multiselect("Top Skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.subheader("Step 3: Behavior Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        q1 = st.radio("I meet deadlines", opts, index=2)
        q2 = st.radio("I collaborate effectively", opts, index=2)
        q3 = st.radio("I adapt well to change", opts, index=2)
        st.session_state.behavior_score = round((score_map[q1] + score_map[q2] + score_map[q3]) / 3 * 20, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.subheader("Step 4: JD Match")
        jd1 = st.text_area("Paste JD 1", key="jd_1")
        jd2 = st.text_area("Paste JD 2", key="jd_2")
        jd_inputs = [jd for jd in [jd1, jd2] if jd.strip()]
        if jd_inputs and "resume_text" in st.session_state:
            jd_scores = match_resume_to_jds(st.session_state.resume_text, jd_inputs)
            st.session_state.jd_scores = jd_scores
            for i, score in enumerate(jd_scores):
                st.write(f"**JD {i+1}** Match Score: {score}%")
            plot_radar(jd_scores)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.subheader("Step 5: Final Score & Summary")
        jd_scores = st.session_state.get("jd_scores", [])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1) if jd_scores else 0
        skill_score = len(st.session_state.get("selected_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        qoh = round((skill_score + behavior + avg_jd) / 3, 1)
        st.metric("💡 Quality of Hire Score", f"{qoh}/100")

# ----- Recruiter View -----
def recruiter_dashboard():
    st.title("🧑‍💼 Recruiter Dashboard")
    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Behavior": 84, "Skill": 92, "Gaps": "Strategic Planning"},
        {"Candidate": "Jasmine", "JD Match": 82, "Behavior": 90, "Skill": 80, "Gaps": "Leadership"},
        {"Candidate": "Andre", "JD Match": 75, "Behavior": 70, "Skill": 78, "Gaps": "Communication"}
    ])
    with st.sidebar:
        st.subheader("🎚️ Adjust Weighting")
        w_jd = st.slider("JD Match", 0, 100, 33)
        w_beh = st.slider("Behavior", 0, 100, 33)
        w_skill = st.slider("Skills", 0, 100, 33)
    total = w_jd + w_beh + w_skill
    if total > 0:
        df["QoH Score"] = (
            df["JD Match"] * w_jd +
            df["Behavior"] * w_beh +
            df["Skill"] * w_skill
        ) / total
    st.dataframe(df)

# ----- Routing -----
st.title("⛵ Welcome to Skippr")
portal = st.radio("Choose your portal:", ["👤 Candidate Portal", "🧑‍💼 Recruiter Portal"])
if portal == "👤 Candidate Portal":
    candidate_journey()
else:
    recruiter_dashboard()
