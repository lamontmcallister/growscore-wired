# Skippr MVP Reboot — Part 1: Fullscreen Login + Clean Routing (Polished UI)

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

# === Supabase Auth Setup ===
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
openai.api_key = OPENAI_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Session State Defaults ===
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

# === Fullscreen Login ===
def show_login():
    st.markdown("""
    <div style='text-align: center; padding: 2rem;'>
        <h1>Welcome to Skippr</h1>
        <p>Let’s get you inside — your growth journey starts here.</p>
    </div>
    """, unsafe_allow_html=True)

    auth_mode = st.radio("Action", ["Login", "Sign Up"], horizontal=True)

    st.markdown("#### No resume? No problem — you’ll upload it next.")
    email = st.text_input("Email", placeholder="e.g. you@skippr.ai", key="email_input")
    password = st.text_input("Password", type="password", placeholder="•••••••• (make it a good one)", key="pass_input")

    col1, col2, _ = st.columns([1,1,2])
    with col1:
        if auth_mode == "Login":
            if st.button("🔓 Login"):
                try:
                    result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.supabase_session = result.session
                    st.session_state.supabase_user = result.user
                    st.session_state.current_page = "candidate"
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
    with col2:
        if auth_mode == "Sign Up":
            if st.button("🆕 Create Account"):
                try:
                    result = supabase.auth.sign_up({"email": email, "password": password})
                    st.success("✅ Account created. Check your inbox to verify.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")

# === Sidebar when logged in ===
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

# === Routing Logic ===
if not st.session_state.supabase_session:
    show_login()
else:
    sidebar_logged_in()
    if st.session_state.recruiter_mode:
        st.write("🚧 Recruiter Dashboard coming in next drop...")
    else:
        st.write("✅ Candidate Journey incoming next...")
        # === Step 2: Job Description Input ===
elif st.session_state.step == 2:
    st.header("Step 2: Paste Job Description")

    default_jd = "Looking for a data-savvy talent operations leader with SQL, reporting, and recruiting analytics expertise."

    job_desc = st.text_area(
        "Paste the job description:",
        value=st.session_state.get("job_desc", default_jd if st.session_state.demo_mode else "")
    )

    if job_desc:
        st.session_state.job_desc = job_desc
        st.success("✅ Job description saved.")

    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state.step -= 1
            st.experimental_rerun()
    with col2:
        if st.button("Next ➡️"):
            st.session_state.step += 1
            st.experimental_rerun()
# Skippr MVP Reboot — Part 3: JD Match Score

# === Step 3: JD Match ===
elif st.session_state.step == 3:
    st.header("Step 3: Resume vs JD Match")

    resume_text = st.session_state.get("resume_text", "")
    job_desc = st.session_state.get("job_desc", "")

    if resume_text and job_desc:
        resume_words = set(resume_text.lower().split())
        jd_words = set(job_desc.lower().split())
        overlap = resume_words.intersection(jd_words)
        match_score = len(overlap) / max(len(jd_words), 1) * 100

        st.session_state.match_score = match_score
        st.metric("Match Score", f"{match_score:.1f}%")

        fig, ax = plt.subplots()
        ax.pie([match_score, 100 - match_score], labels=["Match", "Gap"], autopct='%1.1f%%', startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

    else:
        st.warning("❗ Resume or Job Description missing. Go back to Step 1 or 2.")

    # Navigation
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state.step -= 1
            st.experimental_rerun()
    with col2:
        if st.button("Next ➡️"):
            st.session_state.step += 1
            st.experimental_rerun()
# Skippr MVP Reboot — Part 4: Skill Selection

# === Step 4: Skills ===
elif st.session_state.step == 4:
    st.header("Step 4: Select Your Skills")

    skill_options = [
        "Python", "SQL", "Excel", "Project Management",
        "Recruiting Analytics", "Leadership", "Data Visualization",
        "ATS Systems", "People Operations", "Communication"
    ]

    default_skills = skill_options[:4] if st.session_state.demo_mode else []

    selected_skills = st.multiselect(
        "Choose the skills you’re strongest in:",
        skill_options,
        default=st.session_state.get("skills_selected", default_skills)
    )

    st.session_state.skills_selected = selected_skills

    if selected_skills:
        st.success(f"✅ {len(selected_skills)} skills selected.")

    # Optional freeform skill input
    other = st.text_input("Any other skills you'd like to include?")
    if other:
        st.session_state.skills_selected.append(other)
        st.success("✅ Added to your skills list.")

    # Navigation
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state.step -= 1
            st.experimental_rerun()
    with col2:
        if st.button("Next ➡️"):
            st.session_state.step += 1
            st.experimental_rerun()

