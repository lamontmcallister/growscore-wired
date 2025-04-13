# Skippr — Full Platform: Login + Candidate Journey + Recruiter Dashboard (Polished One-File Build)
# Author: Skippr Team | Built for Demo Perfection

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
except:
    pass

# === Supabase ===
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === OpenAI ===
openai.api_key = st.secrets["openai"]["key"]

# === Session Setup ===
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "step" not in st.session_state:
    st.session_state.step = 1
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "recruiter_mode" not in st.session_state:
    st.session_state.recruiter_mode = False

# === Auth View ===
def show_login():
    st.markdown("""
    <div style='text-align: center; padding: 2rem;'>
        <h1>Welcome to Skippr</h1>
        <p>Login or create your account to begin your candidate journey.</p>
    </div>
    """, unsafe_allow_html=True)

    auth_mode = st.radio("Select Option", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if auth_mode == "Login":
        if st.button("Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = result.user
                st.session_state.supabase_session = result.session
                st.experimental_rerun()
            except Exception as e:
                st.error("Login failed")
    else:
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created — check your email to confirm.")
            except Exception as e:
                st.error("Signup failed")

# === Sidebar ===
def sidebar_logged_in():
    with st.sidebar:
        st.markdown(f"**Logged in as:** `{st.session_state.supabase_user.email}`")
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.supabase_user = None
            st.session_state.supabase_session = None
            st.session_state.step = 1
            st.experimental_rerun()
        st.checkbox("Recruiter View", key="recruiter_mode")
        st.checkbox("Demo Mode", key="demo_mode")

# === Candidate Steps ===
def candidate_step_1():
    st.subheader("Step 1: Upload Resume")
    file = st.file_uploader("Upload Resume PDF", type="pdf")
    resume_text = ""
    if file or st.session_state.demo_mode:
        if st.session_state.demo_mode:
            resume_text = "Experienced leader in recruiting ops, analytics, and systems."
        else:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    resume_text += page.extract_text()
        st.session_state.resume_text = resume_text
        st.text_area("Parsed Resume", resume_text, height=200)
        st.success("✅ Resume loaded.")
    if st.button("Next"):
        st.session_state.step += 1
        st.experimental_rerun()

def candidate_step_2():
    st.subheader("Step 2: Paste Job Description")
    jd = st.text_area("Paste the job description:", "Looking for a recruiting leader with analytics expertise." if st.session_state.demo_mode else "")
    st.session_state.job_desc = jd
    if st.button("Next"):
        st.session_state.step += 1
        st.experimental_rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.experimental_rerun()

def candidate_step_3():
    st.subheader("Step 3: JD Match Score")
    r_words = set(st.session_state.resume_text.lower().split())
    j_words = set(st.session_state.job_desc.lower().split())
    overlap = r_words.intersection(j_words)
    score = len(overlap) / max(len(j_words), 1) * 100
    st.session_state.match_score = score
    st.metric("Match Score", f"{score:.1f}%")
    fig, ax = plt.subplots()
    ax.pie([score, 100 - score], labels=["Match", "Gap"], autopct='%1.1f%%')
    st.pyplot(fig)
    if st.button("Next"):
        st.session_state.step += 1
        st.experimental_rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.experimental_rerun()

def candidate_step_4():
    st.subheader("Step 4: Skills Assessment")
    options = ["Python", "SQL", "ATS", "Recruiting Ops", "Stakeholder Management"]
    selected = st.multiselect("Select your skills:", options, default=options[:3] if st.session_state.demo_mode else [])
    st.session_state.skills = selected
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
    st.text_input("Backchannel Contact")
    st.info("🚧 Reference verification in progress — demo only.")
    if st.button("Next"):
        st.session_state.step += 1
        st.experimental_rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.experimental_rerun()

def candidate_step_6():
    st.subheader("Step 6: Education + HR Check")
    st.text_input("Highest Degree")
    st.text_input("Institution")
    st.info("🚧 HR performance verification coming soon")
    if st.button("Next"):
        st.session_state.step += 1
        st.experimental_rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.experimental_rerun()

def candidate_step_7():
    st.subheader("Step 7: Quality of Hire Summary")
    match = st.session_state.get("match_score", 0)
    skills = len(st.session_state.get("skills", [])) * 10
    refs = 20
    edu = 10
    qoh = (match + skills + refs + edu) / 4
    st.metric("QoH Score", f"{qoh:.1f}")
    st.progress(int(qoh))
    st.success("🎉 Candidate Journey Complete!")
    if st.button("Back"):
        st.session_state.step -= 1
        st.experimental_rerun()

# === Recruiter Dashboard ===
def recruiter_dashboard():
    st.title("Recruiter Dashboard")
    st.subheader("Candidate Comparison")
    candidates = pd.DataFrame({
        "Candidate": ["You", "Demo User"],
        "QoH Score": [st.session_state.get("match_score", 0) + 30, 72.5],
        "Match %": [st.session_state.get("match_score", 0), 68],
        "Skills Gap": ["2 missing", "3 missing"]
    })
    st.dataframe(candidates, use_container_width=True)
    st.subheader("Adjust QoH Weights")
    st.slider("Match % Weight", 0, 100, 25)
    st.slider("Skills Weight", 0, 100, 25)
    st.slider("References Weight", 0, 100, 25)
    st.slider("Education Weight", 0, 100, 25)
    st.subheader("AI Recommendation")
    st.markdown("✅ Candidate A is a strong match.\n⚠️ Candidate B shows gaps.")

# === Routing ===
if not st.session_state.supabase_session:
    show_login()
else:
    sidebar_logged_in()
    if st.session_state.recruiter_mode:
        recruiter_dashboard()
    else:
        step = st.session_state.step
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
            st.success("🎯 You’ve completed the candidate journey.")
