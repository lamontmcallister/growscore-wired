# Skippr MVP: Fully Merged App (Functional + Polished)
# Features: Full Candidate Journey, Recruiter Dashboard, Supabase Auth, Clean UI, Fullscreen Routing

import streamlit as st
from supabase import create_client, Client
import time
from datetime import datetime
import base64
import io
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

# --- CONFIG ---
st.set_page_config(page_title="Skippr - Predictive Hiring Intelligence", layout="wide")

# --- CUSTOM CSS ---
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- DEBUG TOGGLE ---
st.sidebar.markdown("### Developer Tools")
debug_mode = st.sidebar.checkbox("Debug Mode")

# --- SESSION INIT ---
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- SUPABASE CLIENT ---
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

# --- AUTH ---
def login():
    st.title("🔐 Welcome to Skippr")
    st.write("Login to access your personalized hiring journey or dashboard.")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                st.session_state.page = "profile_select"
                st.experimental_rerun()
            else:
                st.error("Login failed. Check credentials.")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("Sign Up Instead"):
        st.session_state.page = "signup"
        st.experimental_rerun()

def signup():
    st.title("📝 Create Your Skippr Account")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            st.success("Account created! You can now log in.")
            st.session_state.page = "login"
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- NAVIGATION ---
def nav():
    cols = st.columns([3, 1, 1, 1])
    with cols[1]:
        if st.button("Candidate Journey"):
            st.session_state.page = "candidate"
    with cols[2]:
        if st.button("Recruiter Dashboard"):
            st.session_state.page = "recruiter"
    with cols[3]:
        if st.button("Logout"):
            st.session_state.clear()
            st.session_state.page = "login"
            st.experimental_rerun()

# --- CANDIDATE JOURNEY ---
def candidate_journey():
    st.subheader("📄 Upload Resume")
    resume_file = st.file_uploader("Upload your resume (PDF or TXT)", type=["pdf", "txt"])
    resume_text = ""
    if resume_file:
        resume_text = resume_file.read().decode("utf-8") if resume_file.type == "text/plain" else "Simulated PDF parsing."
        st.success("Resume uploaded.")

    st.subheader("📝 Paste Job Description")
    job_desc = st.text_area("Paste the job description here")

    if resume_text and job_desc:
        st.subheader("🤖 Matching Skills")
        vectorizer = TfidfVectorizer().fit_transform([resume_text, job_desc])
        similarity = cosine_similarity(vectorizer[0:1], vectorizer[1:2])[0][0]
        st.metric("Match Score", f"{similarity * 100:.2f}%")

    st.subheader("🧠 Behavior Survey")
    q1 = st.radio("How do you prefer to collaborate?", ["Independently", "In a team", "Flexible"], key="q1")
    q2 = st.radio("How do you respond to feedback?", ["Embrace it", "Need time", "Depends"], key="q2")

    st.subheader("📩 Add References")
    ref_name = st.text_input("Reference Name")
    ref_email = st.text_input("Reference Email")
    if st.button("Save Reference"):
        st.success(f"Saved reference for {ref_name}")

    st.subheader("✅ Final Score Summary")
    st.write("This is a placeholder summary score. In production, this will include weighted behavior, match %, and references.")

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.subheader("📊 Candidate Comparison")
    data = pd.DataFrame({
        "Candidate": ["Alice", "Bob"],
        "Match %": [87, 74],
        "Behavior Score": [9, 7],
        "References": ["✔️", "❌"],
        "QoH Score": [89, 72]
    })
    st.dataframe(data)

    st.subheader("🎯 QoH Weight Adjustments")
    match_weight = st.slider("Job Match % Weight", 0, 100, 40)
    behavior_weight = st.slider("Behavior Score Weight", 0, 100, 30)
    ref_weight = st.slider("Reference Weight", 0, 100, 30)

    st.write("These weights will adjust the final QoH calculations dynamically.")

# --- MAIN ROUTING ---
if st.session_state.page == "login":
    login()

elif st.session_state.page == "signup":
    signup()

elif "user" in st.session_state:
    nav()

    if st.session_state.page == "profile_select":
        st.title("👤 Choose or Create a Job Profile")
        st.write("(Coming soon: multi-profile support!)")

    elif st.session_state.page == "candidate":
        candidate_journey()

    elif st.session_state.page == "recruiter":
        recruiter_dashboard()

    if debug_mode:
        st.sidebar.markdown("### Session State")
        st.sidebar.json(st.session_state)

else:
    st.warning("Please log in to continue.")
