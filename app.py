import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- STYLING ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] {
                font-family: 'Segoe UI', sans-serif;
                padding: 0rem !important;
            }
            h1, h2, h3 {
                font-weight: 600 !important;
                margin-bottom: 0.5rem;
            }
            div.stButton > button {
                background-color: #ff6a00;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0.5rem 1.2rem;
                font-weight: 600;
                font-size: 1rem;
                margin-top: 0.5rem;
            }
            section[data-testid="stSidebar"] {
                background-color: #f9f4ef;
                border-right: 1px solid #e1dfdb;
            }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION STATE ---
for k in ["supabase_session", "supabase_user", "step", "profiles", "active_profile_id"]:
    if k not in st.session_state:
        st.session_state[k] = 0 if k == "step" else None

# --- SUPABASE PROFILE HELPERS ---
def fetch_profiles(user_email):
    res = supabase.table("user_profiles").select("*").eq("user_email", user_email).execute()
    if res.data:
        return res.data
    return []

def save_profile_to_db(profile_id, data):
    supabase.table("user_profiles").update({"data": data}).eq("id", profile_id).execute()

def create_profile_in_db(user_email, name):
    new_profile = supabase.table("user_profiles").insert({
        "user_email": user_email,
        "name": name,
        "data": {}
    }).execute()
    return new_profile.data[0] if new_profile.data else None

# --- SKILLS / GPT HELPERS ---
skills_pool = ["Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
               "Communication", "Strategic Planning", "Excel", "Project Management"]

def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\n{text}\nReturn as a Python list."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
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
        return ast.literal_eval(res.choices[0].message.content.strip())
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
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return [np.random.randint(70, 90) for _ in jd_texts]

# --- PROFILE SELECTOR ---
def profile_selector(user_email):
    st.markdown("### 👤 Select or Create a Candidate Profile")
    profiles = fetch_profiles(user_email)
    profile_names = [p["name"] for p in profiles]

    if profile_names:
        selected = st.selectbox("Choose a Profile", profile_names)
        if st.button("Load Selected Profile"):
            selected_profile = next((p for p in profiles if p["name"] == selected), None)
            st.session_state.active_profile_id = selected_profile["id"]
            st.session_state.profile_data = selected_profile["data"]
            st.success(f"Profile '{selected}' loaded!")

    new_profile_name = st.text_input("Or Create New Profile")
    if new_profile_name and st.button("Create New Profile"):
        new_profile = create_profile_in_db(user_email, new_profile_name)
        if new_profile:
            st.session_state.active_profile_id = new_profile["id"]
            st.session_state.profile_data = new_profile["data"]
            st.success(f"Created new profile: {new_profile_name}")

# --- CANDIDATE JOURNEY (Steps 0-5) ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Contact Info")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state["resume_contact"] = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        selected = st.multiselect("Choose your strongest skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.caption("How do you show up at work?")
        behavior_questions = {
            "Meets deadlines consistently": None,
            "Collaborates well in teams": None,
            "Adapts quickly to change": None,
            "Demonstrates leadership": None,
            "Communicates effectively": None,
        }
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        for i, question in enumerate(behavior_questions):
            response = st.radio(question, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (len(behavior_questions) * 5)) * 100, 1)
        st.session_state.behavior_score = behavior_score
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    # --- SAVE DATA TO SUPABASE ---
    if st.session_state.active_profile_id:
        profile_data = {
            "resume_text": st.session_state.get("resume_text", ""),
            "selected_skills": st.session_state.get("selected_skills", []),
            "behavior_score": st.session_state.get("behavior_score", 0),
            "resume_contact": st.session_state.get("resume_contact", {})
        }
        save_profile_to_db(st.session_state.active_profile_id, profile_data)

# --- ROUTING ---
if st.session_state.supabase_user:
    user_email = st.session_state.supabase_user.email
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        if not st.session_state.active_profile_id:
            profile_selector(user_email)
        else:
            candidate_journey()
else:
    st.markdown("### Please log in to continue.")
