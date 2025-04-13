# Skippr app.py — Complete Platform with Login, Candidate Journey, and Recruiter Dashboard

import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Skippr", layout="wide")

# === Load CSS ===
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ Custom CSS not found. Using default styling.")

# === Secrets ===
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
openai.api_key = OPENAI_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Session State ===
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "step" not in st.session_state:
    st.session_state.step = 1
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "recruiter_mode" not in st.session_state:
    st.session_state.recruiter_mode = False

# === Login Page ===
def show_login():
    st.markdown("""
    <div style='text-align: center; padding: 2rem;'>
        <h1>Welcome to Skippr</h1>
        <p>Login or sign up to begin your personalized candidate journey.</p>
    </div>
    """, unsafe_allow_html=True)

    auth_mode = st.radio("Choose an option", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if auth_mode == "Login":
        if st.button("Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.session_state.current_page = "candidate"
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("Create Account"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Check your inbox to verify.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# === Sidebar (after login) ===
def sidebar_logged_in():
    with st.sidebar:
        st.markdown(f"**Logged in as:** `{st.session_state.supabase_user.email}`")
        if st.button("Log Out"):
            supabase.auth.sign_out()
            st.session_state.supabase_session = None
            st.session_state.supabase_user = None
            st.session_state.current_page = "login"
            st.experimental_rerun()
        st.checkbox("Recruiter View", key="recruiter_mode")
        st.checkbox("Demo Mode", key="demo_mode")

# === Recruiter Dashboard ===
def recruiter_dashboard():
    st.title("Recruiter Dashboard")
    st.subheader("Candidate Comparison Table")

    # Sample candidate data
    candidates = pd.DataFrame({
        "Candidate": ["You", "Demo User"],
        "QoH Score": [st.session_state.get("match_score", 0) + 30, 72.5],
        "Match %": [st.session_state.get("match_score", 0), 68.0],
        "Skills Gap": ["2 missing", "3 missing"],
    })
    st.dataframe(candidates, use_container_width=True)

    st.subheader("Adjust QoH Weights")
    match_weight = st.slider("JD Match %", 0, 100, 25)
    skill_weight = st.slider("Skills", 0, 100, 25)
    ref_weight = st.slider("References", 0, 100, 25)
    ed_weight = st.slider("Education", 0, 100, 25)
    total_weight = match_weight + skill_weight + ref_weight + ed_weight

    if total_weight != 100:
        st.warning("⚠️ Total weight must equal 100% for accurate scoring.")

    st.subheader("AI Recommendation")
    st.markdown("✅ Candidate A is a strong match. Suggest interview.\n\n⚠️ Candidate B has gaps — consider a growth plan.")

# === Routing ===
if not st.session_state.supabase_session:
    show_login()
else:
    sidebar_logged_in()
    if st.session_state.recruiter_mode:
        recruiter_dashboard()
    else:
        st.title("Candidate Journey")
        step = st.session_state.step

        def candidate_step_1():
            st.subheader("Step 1: Upload Your Resume")
            resume_file = st.file_uploader("Upload PDF", type="pdf")
            resume_text = ""
            if resume_file or st.session_state.demo_mode:
                if st.session_state.demo_mode:
                    resume_text = "Experience in recruiting ops, analytics, and systems. Skilled in SQL, Python, Tableau."
                else:
                    with pdfplumber.open(resume_file) as pdf:
                        for page in pdf.pages:
                            resume_text += page.extract_text()
                st.session_state.resume_text = resume_text
                st.success("✅ Resume processed.")
                st.text_area("Resume Text", resume_text, height=200)
            if st.button("Next"):
                st.session_state.step += 1
                st.experimental_rerun()

        def candidate_step_2():
            st.subheader("Step 2: Paste Job Description")
            job_desc = st.text_area("Paste JD:", "Looking for a recruiting leader with analytics expertise." if st.session_state.demo_mode else "")
            st.session_state.job_desc = job_desc
            if st.button("Next"):
                st.session_state.step += 1
                st.experimental_rerun()
            if st.button("Back"):
                st.session_state.step -= 1
                st.experimental_rerun()

        def candidate_step_3():
            st.subheader("Step 3: JD Match Score")
            resume_words = set(st.session_state.resume_text.lower().split())
            jd_words = set(st.session_state.job_desc.lower().split())
            overlap = resume_words.intersection(jd_words)
            score = len(overlap) / max(len(jd_words), 1) * 100
            st.session_state.match_score = score
            st.metric("Match Score", f"{score:.1f}%")
            fig, ax = plt.subplots()
            ax.pie([score, 100 - score], labels=["Match", "Gap"], autopct='%1.1f%%')
            ax.axis("equal")
            st.pyplot(fig)
            if st.button("Next"):
                st.session_state.step += 1
                st.experimental_rerun()
            if st.button("Back"):
                st.session_state.step -= 1
                st.experimental_rerun()

        def candidate_step_4():
            st.subheader("Step 4: Skills Assessment")
            options = ["Python", "SQL", "Recruiting", "Data Analysis", "Stakeholder Management"]
            skills_selected = st.multiselect("Select your skills:", options, default=options[:3] if st.session_state.demo_mode else [])
            st.session_state.skills = skills_selected
            if st.button("Next"):
                st.session_state.step += 1
                st.experimental_rerun()
            if st.button("Back"):
                st.session_state.step -= 1
                st.experimental_rerun()

        def candidate_step_5():
            st.subheader("Step 5: References & Backchannel")
            st.text_input("Reference Name")
            st.text_input("Reference Email")
            st.text_input("Backchannel Contact (Optional)")
            st.markdown("🚧 Reference functionality coming soon")
            if st.button("Next"):
                st.session_state.step += 1
                st.experimental_rerun()
            if st.button("Back"):
                st.session_state.step -= 1
                st.experimental_rerun()

        def candidate_step_6():
            st.subheader("Step 6: Education + HR Check")
            st.text_input("Highest Degree")
            st.text_input("School / University")
            st.markdown("🚧 HR Performance Request (Coming Soon)")
            if st.button("Next"):
                st.session_state.step += 1
                st.experimental_rerun()
            if st.button("Back"):
                st.session_state.step -= 1
                st.experimental_rerun()

        def candidate_step_7():
            st.subheader("Step 7: Quality of Hire (QoH) Summary")
            score = st.session_state.get("match_score", 0)
            skill_score = len(st.session_state.get("skills", [])) * 10
            ref_score = 20
            edu_score = 10
            total = (score + skill_score + ref_score + edu_score) / 4
            st.metric("QoH Score", f"{total:.1f}")
            st.progress(int(total))
            st.success("Candidate Journey Complete 🎉")
            if st.button("Back"):
                st.session_state.step -= 1
                st.experimental_rerun()

        if step == 1:
            candidate_step_1()
        elif step == 2:
            candidate_step_2()
        elif step == 3:
            candidate_step_3()
        elif step == 4:
            candidate_step_4()
        elif step == 5:
            candidate_step_5()
        elif step == 6:
            candidate_step_6()
        elif step == 7:
            candidate_step_7()
        else:
            st.success("✅ Candidate journey complete.")
