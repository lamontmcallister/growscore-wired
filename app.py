
import streamlit as st
import base64
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from supabase import create_client, Client
from datetime import datetime

# Config
st.set_page_config(page_title="Skippr", layout="wide", page_icon="⛵")

# Load Secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Background CSS
st.markdown(
    """
    <style>
        .main {
            background: linear-gradient(to right, #f8fbff, #e6f0ff);
            color: #222;
        }
        .block-container {
            padding-top: 2rem;
        }
        .stButton>button {
            border-radius: 8px;
            padding: 0.5em 1em;
            font-weight: bold;
            background-color: #1f77b4;
            color: white;
        }
        .stTextInput>div>div>input {
            border-radius: 6px;
        }
        h1, h2, h3 {
            color: #1f77b4;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session State Defaults
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# Logo & Branding
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
with col2:
    st.title("Skippr")
    st.caption("🚀 Skip the line. Get the job.")

# Auth UI
with st.sidebar:
    st.header("🔐 Login or Register")
    mode = st.radio("Select", ["Login", "Register"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if mode == "Login":
        if st.button("Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.success("✅ Logged in!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Verify your email.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

if not st.session_state.supabase_session:
    st.stop()

# ----------------------- Candidate Journey -----------------------

def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:
{text}
Return as a Python list."
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
    prompt = f"Extract the full name, email, and job title from this resume:
{text}
Return a dictionary."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return eval(res.choices[0].message.content.strip())
    except:
        return {"name": "", "email": "", "title": ""}

def match_resume_to_jds(resume_text, jd_texts):
    prompt = f"Given this resume:
{resume_text}

Match semantically to the following JDs:
"
    for i, jd in enumerate(jd_texts):
        prompt += f"
JD {i+1}:
{jd}
"
    prompt += "
Return a list of match scores, e.g. [82, 76]"
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

def candidate_journey():
    st.header("🌱 Candidate Journey")
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)
    st.progress((step + 1) / 6)

    if step == 0:
        st.subheader("Step 1: Resume Upload & Contact Info")
        uploaded = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])
        if uploaded:
            if uploaded.type == "application/pdf":
                with pdfplumber.open(uploaded) as pdf:
                    text = "
".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            else:
                text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state.contact_info = extract_contact_info(text)
            st.success("Resume processed!")

        st.button("Next", on_click=next_step)

    elif step == 1:
        st.subheader("Step 2: Review Skills")
        st.multiselect("Review skills:", st.session_state.get("resume_skills", []), key="confirmed_skills")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.subheader("Step 3: Match Resume to Job Descriptions")
        jd1 = st.text_area("Paste JD 1")
        jd2 = st.text_area("Paste JD 2")
        jd_inputs = [jd for jd in [jd1, jd2] if jd.strip()]
        if jd_inputs and "resume_text" in st.session_state:
            jd_scores = match_resume_to_jds(st.session_state.resume_text, jd_inputs)
            st.session_state.jd_scores = jd_scores
            for i, score in enumerate(jd_scores):
                st.write(f"JD {i+1} Match Score: {score}%")
            plot_radar(jd_scores)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.subheader("Step 4: Behavior Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        q1 = st.radio("I meet deadlines", opts, index=2)
        q2 = st.radio("I collaborate well", opts, index=2)
        q3 = st.radio("I adapt to change", opts, index=2)
        st.session_state.behavior_score = round((score_map[q1] + score_map[q2] + score_map[q3]) / 3 * 20, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.subheader("Step 5: Education")
        degree = st.text_input("Degree")
        major = st.text_input("Major")
        school = st.text_input("School")
        year = st.text_input("Graduation Year")
        st.session_state.education = f"{degree} in {major}, {school}, {year}"
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.subheader("✅ Final Summary")
        jd_scores = st.session_state.get("jd_scores", [])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1) if jd_scores else 0
        skill_score = len(st.session_state.get("confirmed_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        qoh = round((skill_score + behavior + avg_jd) / 3, 1)
        st.metric("Quality of Hire Score", f"{qoh}/100")

# ----------------------- Recruiter Dashboard -----------------------

def recruiter_dashboard():
    st.header("🧑‍💼 Recruiter Dashboard")
    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Behavior": 84, "Skill": 92},
        {"Candidate": "Jasmine", "JD Match": 82, "Behavior": 90, "Skill": 80},
        {"Candidate": "Andre", "JD Match": 75, "Behavior": 70, "Skill": 78}
    ])
    df["QoH"] = round((df["JD Match"] + df["Behavior"] + df["Skill"]) / 3, 1)
    st.dataframe(df)

# ----------------------- Routing -----------------------

portal = st.radio("Choose your portal:", ["Candidate", "Recruiter"])
if portal == "Candidate":
    candidate_journey()
else:
    recruiter_dashboard()
