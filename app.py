# Skippr — Full MVP (Part 1: Candidate Journey + Demo & Pilot Modes)

import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from supabase import create_client, Client

# === Page Config ===
st.set_page_config(page_title="Skippr", layout="wide")

# === Load CSS ===
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ Custom CSS not found. Using default styling.")

# === Secrets & Supabase Setup ===
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
openai.api_key = OPENAI_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Session State ===
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "profile_data" not in st.session_state:
    st.session_state.profile_data = {}

# === Sidebar Login ===
with st.sidebar:
    st.header("Login to Skippr")
    auth_mode = st.radio("Choose", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if auth_mode == "Login":
        if st.button("Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.success(f"✅ Logged in as {email}")
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check your inbox to verify.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

if not st.session_state.supabase_session:
    st.warning("⚠️ Please log in to continue.")
    st.stop()

# === Hero Header ===
st.markdown("""
<div style='text-align: center; padding: 2rem 0;'>
    <h1 style='font-size: 3rem; margin-bottom: 0.2rem;'>Welcome to Skippr</h1>
    <p style='font-size: 1.2rem; color: #555;'>Predictive hiring intelligence. Powered by AI. Backed by human potential.</p>
</div>
""", unsafe_allow_html=True)

# === Demo Mode Toggle ===
demo_mode = st.checkbox("Demo Mode", value=False, help="Use pre-filled resume and JD for demo purposes.")
if demo_mode:
    st.info("✅ Demo Mode is ON — sample data loaded below.")

# === Candidate Journey ===
st.header("Candidate Journey")

# Step 1: Resume Upload
st.subheader("1. Upload Your Resume")
resume_file = st.file_uploader("Upload PDF", type="pdf")
resume_text = ""

if resume_file or demo_mode:
    if demo_mode:
        resume_text = "Experienced leader in operations, recruiting analytics, and talent systems. Skilled in Python, SQL, stakeholder communication."
    else:
        with pdfplumber.open(resume_file) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text()
    st.success("✅ Resume processed.")
    st.text_area("Resume Text", resume_text, height=200)

# Step 2: Job Description
st.subheader("2. Paste Job Description")
job_desc = st.text_area("Paste the JD:", "" if not demo_mode else "Looking for a Director of Recruiting Ops to lead reporting, analytics, and cross-functional hiring initiatives.")

# Step 3: JD Matching
if resume_text and job_desc:
    st.subheader("3. Resume vs JD Match")
    resume_words = set(resume_text.lower().split())
    jd_words = set(job_desc.lower().split())
    overlap = resume_words.intersection(jd_words)
    match_score = len(overlap) / max(len(jd_words), 1) * 100
    st.metric("Match Score", f"{match_score:.1f}%")

    fig, ax = plt.subplots()
    ax.pie([match_score, 100 - match_score], labels=["Match", "Gap"], autopct='%1.1f%%', startangle=90)
    ax.axis("equal")
    st.pyplot(fig)

    # Save to Supabase if not in Demo Mode
    if not demo_mode:
        try:
            user_id = st.session_state.supabase_user.id
            timestamp = datetime.utcnow().isoformat()
            supabase.table("matches").insert({
                "user_id": user_id,
                "resume_text": resume_text,
                "job_description": job_desc,
                "match_score": match_score,
                "timestamp": timestamp
            }).execute()
            st.success("📬 Data saved to Supabase.")
        except Exception as e:
            st.warning(f"Could not save: {e}")

# (More candidate journey steps like Skills, References, QoH, etc. to follow in next part...)

st.caption("Data shown above is for MVP preview only. Log in with your resume to test your own match score.")
# Skippr — Full MVP (Part 2: Skills, References, QoH, Recruiter Dashboard)

# === Candidate Journey Continued ===

st.subheader("4. Skills Assessment")
skill_options = ["Python", "SQL", "Data Analysis", "Leadership", "Project Management", "Communication"]
skills_selected = st.multiselect("Select your skills:", skill_options, default=skill_options[:3] if demo_mode else [])

st.subheader("5. Add Education")
edu_text = st.text_input("Highest Degree or School Name", "MBA in Finance - NYU" if demo_mode else "")

st.subheader("6. References")
reference_1 = st.text_input("Reference Name", "Jane Smith" if demo_mode else "")
reference_email = st.text_input("Reference Email", "jane@example.com" if demo_mode else "")
if reference_1 and reference_email:
    st.success("✅ Reference saved.")

st.subheader("7. Backchannel Input")
backchannel = st.text_area("Name someone who has worked with the company/team you're applying to (optional):")

st.subheader("8. HR Performance Check (Optional)")
st.text("[Not functional yet – coming soon]")

# === QoH Score Calculation ===
st.subheader("9. Quality of Hire (QoH) Score")
score_components = {
    "JD Match": match_score if resume_text and job_desc else 0,
    "Skills": len(skills_selected) * 10,
    "References": 20 if reference_1 else 0,
    "Education": 10 if edu_text else 0
}

total_qoh = sum(score_components.values()) / 4
st.metric("Final QoH Score", f"{total_qoh:.1f}")

st.progress(int(total_qoh))

# === Recruiter Dashboard ===
st.header("Recruiter Dashboard")

# Example candidate comparison table
st.subheader("Candidate Comparison")
data = {
    "Candidate": ["You", "Demo User"],
    "QoH Score": [total_qoh, 72.5],
    "Match %": [match_score if resume_text and job_desc else 0, 68.0],
    "Skills Gap": ["2 missing", "3 missing"]
}
df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True)

# Adjustable Weight Sliders
st.subheader("Adjust QoH Weighting")
match_weight = st.slider("JD Match %", 0, 100, 25)
skill_weight = st.slider("Skills", 0, 100, 25)
ref_weight = st.slider("References", 0, 100, 25)
ed_weight = st.slider("Education", 0, 100, 25)

st.caption("Adjust the sliders to model your ideal candidate profile.")

# === AI Recommendations Placeholder ===
st.subheader("AI Hiring Recommendations")
st.markdown("✅ Candidate A is a strong match. Suggest interview.\n\n⚠️ Candidate B has skill gaps — recommend development plan.")

# === Footer ===
st.caption("Built with ❤️ by Skippr. Human-centered hiring for a smarter future.")
