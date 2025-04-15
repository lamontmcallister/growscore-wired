# Skippr App – Final MVP: Sidebar Login + Hero + Toggle Views
import streamlit as st
import os
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="Skippr", layout="wide")

# Load CSS
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Load secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Session state
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Candidate"

# Sidebar login/signup
with st.sidebar:
    st.header("👤 Welcome to Skippr")
    auth_mode = st.radio("Login or Sign Up", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if auth_mode == "Login" and st.button("Login"):
        try:
            user = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.supabase_session = user.session
            st.session_state.supabase_user = user.user
            st.success("✅ Logged in successfully!")
        except Exception as e:
            st.error(f"Login failed: {e}")

    elif auth_mode == "Sign Up" and st.button("Sign Up"):
        try:
            user = supabase.auth.sign_up({"email": email, "password": password})
            st.success("✅ Account created. Please check your email.")
        except Exception as e:
            st.error(f"Sign up failed: {e}")

    if st.session_state.supabase_user:
        try:
            email_display = st.session_state.supabase_user.email
        except AttributeError:
            email_display = st.session_state.supabase_user["email"]
        st.markdown(f"Logged in as: `{email_display}`")
        if st.button("Logout"):
            st.session_state.supabase_session = None
            st.session_state.supabase_user = None
            st.success("🔒 Logged out")

# Top-right view toggle
st.markdown("<div style='position: fixed; top: 10px; right: 20px; z-index: 999;'>", unsafe_allow_html=True)
mode = st.radio("Mode", ["Candidate", "Recruiter"], horizontal=True, key="mode_toggle")
st.session_state.view_mode = mode
st.markdown("</div>", unsafe_allow_html=True)

# Main center panel
if not st.session_state.supabase_user:
    st.markdown("""
    <h1 style='font-size: 3em; font-weight: bold;'>🚀 Skippr is Your Superpower</h1>
    <h3 style='color: #777;'>Smarter Hiring. Verified Potential. Real Results.</h3>
    <hr style='border: 1px solid #eee;'>
    <h4>🌟 Why Skippr?</h4>
    <ul style='line-height: 1.8;'>
      <li>🧠 Stand out with a predictive <b>Quality of Hire (QoH)</b> score</li>
      <li>✅ Back up your profile with <b>verified references and real skills</b></li>
      <li>🧭 Instantly match your resume to any job description</li>
      <li>💡 Built to <b>amplify your potential</b>, not just echo your past</li>
    </ul>
    """, unsafe_allow_html=True)
    st.image("https://images.unsplash.com/photo-1519389950473-47ba0277781c", use_column_width=True)
else:
    if st.session_state.view_mode == "Candidate":
        st.header("🎯 Candidate Journey")
        st.subheader("Step 1: Upload Your Resume")
        st.file_uploader("Upload resume as PDF", type=["pdf"])
        st.subheader("Step 2: Add Education")
        st.text_input("School Name")
        st.text_input("Degree")
        st.text_input("Graduation Year")
        st.subheader("Step 3: Enter References")
        st.text_input("Reference Name")
        st.text_input("Reference Email")
        st.subheader("Step 4: Match to Job Descriptions")
        st.text_area("Paste job description")
        st.button("Analyze Fit")
        st.subheader("Final Step: Review Your Quality of Hire Score")
        st.metric("Quality of Hire", "82", delta="+12")
    else:
        st.header("📊 Recruiter Dashboard")
        st.subheader("Candidate Comparison Table")
        st.dataframe(pd.DataFrame({
            "Candidate": ["Jordan", "Alex", "Taylor"],
            "QoH Score": [82, 76, 90],
            "Match %": [88, 80, 95],
            "Reference Score": [5, 4, 5]
        }))

        st.subheader("Adjust QoH Weights")
        st.slider("Resume Match Weight", 0, 100, 40)
        st.slider("Reference Score Weight", 0, 100, 30)
        st.slider("Education Score Weight", 0, 100, 30)

        st.subheader("📌 AI Recommendations")
        st.success("Jordan is a strong fit based on role alignment and references.")
