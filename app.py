import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
import json
from supabase import create_client, Client
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- CUSTOM STYLING ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; padding: 0rem !important; }
            h1, h2, h3 { font-weight: 600 !important; margin-bottom: 0.5rem; }
            div.stButton > button { background-color: #ff6a00; color: white; border: none; border-radius: 6px; padding: 0.5rem 1.2rem; font-weight: 600; font-size: 1rem; margin-top: 0.5rem; }
            .stSlider > div { padding-top: 0.5rem; }
            section[data-testid="stSidebar"] { background-color: #f9f4ef; border-right: 1px solid #e1dfdb; }
            .markdown-block { background-color: #f8f8f8; padding: 1rem 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 1rem; }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION STATE ---
for k in ["supabase_session", "supabase_user", "step", "profiles", "active_profile"]:
    if k not in st.session_state:
        st.session_state[k] = 0 if k == "step" else {} if k == "profiles" else None

# --- UTILS ---
skills_pool = [
    "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
    "Communication", "Strategic Planning", "Excel", "Project Management"
]

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

def calculate_qoh_score(skill_count, ref, behav, jd_scores):
    avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
    skills = skill_count * 5
    final = round((skills + ref + behav + avg_jd) / 4, 1)
    return final, {"Skills": skills, "References": ref, "Behavior": behav, "JD Match": avg_jd}

# --- PROFILE MANAGEMENT ---
def profile_management():
    st.title("👤 Profile Management")
    user_email = st.session_state.supabase_user.email
    try:
        profiles = supabase.table("profiles").select("*").eq("user_email", user_email).execute()
    except Exception:
        st.error("❌ Failed to fetch profiles. Please try again later.")
        st.stop()

    profile_names = [p["name"] for p in profiles.data] if profiles.data else []
    st.write("Choose a profile or create a new one:")

    selected = st.selectbox("Select Profile", ["Create New"] + profile_names if profile_names else ["Create New"])

    if selected == "Create New":
        new_name = st.text_input("Enter New Profile Name")
        if st.button("Start with New Profile") and new_name:
            if new_name in profile_names:
                st.warning("Profile name already exists. Choose another name.")
            else:
                st.session_state.active_profile = new_name
                st.session_state.step = 0
                st.rerun()
    elif selected:
        st.session_state.active_profile = selected
        st.session_state.step = 0
        profile_data = next((p for p in profiles.data if p["name"] == selected), {})
        st.write(f"**Job Title**: {profile_data.get('job_title', 'N/A')}")
        st.write(f"**QoH Score**: {profile_data.get('qoh_score', 'N/A')}")
        if st.button(f"Edit Profile: {selected}"):
            st.rerun()
        if st.button(f"Delete Profile: {selected}"):
            try:
                supabase.table("profiles").delete().eq("name", selected).eq("user_email", user_email).execute()
                st.success(f"Deleted profile: {selected}")
                st.rerun()
            except Exception:
                st.error("Failed to delete profile.")

# --- LOGIN UI ---
def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=350)
        st.markdown("### From Rejection to Revolution")
        st.caption("💡 I didn’t get the job. I built the platform that fixes the problem.")

    st.markdown("---")

    with st.sidebar:
        st.header("🔐 Log In or Create Account")
        mode = st.radio("Choose Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.success("✅ Logged in successfully.")
                st.rerun()
            except:
                st.error("Login failed. Please check your credentials.")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email.")
            except:
                st.error("Signup failed. Try again with a different email.")

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        profile_management()
        if st.session_state.active_profile:
            candidate_journey()  # Assuming candidate_journey() remains unchanged
    else:
        recruiter_dashboard()  # Assuming recruiter_dashboard() remains unchanged
else:
    login_ui()
