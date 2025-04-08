
import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="Skippr by GrowScore", layout="wide")

# Load secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

def login_ui():
    st.markdown("""
    <style>
        .login-box {
            background-color: #f4f4f4;
            padding: 2rem;
            border-radius: 10px;
            max-width: 400px;
            margin: auto;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .login-title {
            text-align: center;
            font-size: 28px;
            margin-bottom: 1rem;
            color: #262730;
        }
    </style>
    <div class="login-box">
        <div class="login-title">Welcome to Skippr</div>
    """, unsafe_allow_html=True)

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
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("🆕 Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check your email to verify.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.supabase_session:
    login_ui()
    st.stop()

st.title("🚀 Skippr – Your Shortcut to Better Hiring")

portal = st.radio("Choose your portal:", ["👤 Candidate Portal", "🧑‍💼 Recruiter Portal"], horizontal=True)

def candidate_journey():
    st.header("🌱 Candidate Journey")
    st.write("All original steps of the journey go here... (resume upload, JD match, references, verification, etc.)")

def recruiter_dashboard():
    st.header("🧑‍💼 Recruiter Dashboard")
    st.write("Candidate comparison table, AI recs, QoH scoring, etc.")

if portal == "👤 Candidate Portal":
    candidate_journey()
else:
    recruiter_dashboard()
