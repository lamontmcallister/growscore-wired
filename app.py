# Skippr App – Sidebar Login with Centered Landing Page
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
        st.markdown(f"Logged in as: `{st.session_state.supabase_user['email']}`")
        if st.button("Logout"):
            st.session_state.supabase_session = None
            st.session_state.supabase_user = None
            st.success("🔒 Logged out")

# Main area (center)
if not st.session_state.supabase_user:
    st.title("🚀 Welcome to Skippr")
    st.subheader("Predictive Hiring, Verified Potential")
    st.markdown("""
    **Why Skippr?**
    - Get noticed faster with a Quality of Hire score
    - Show verified references and skills
    - See how you stack up against any job description
    - Built to support *your* potential, not just your past titles
    """)
    st.image("https://images.unsplash.com/photo-1519389950473-47ba0277781c", use_column_width=True)
else:
    st.success("🎉 You are logged in! Proceed to the Candidate Journey")
    st.write("[Insert Candidate Journey modules here – resume upload, profile, JD match, etc.]")

# Optional top-right recruiter toggle
with st.container():
    st.markdown("""
        <style>
        .css-1q7gj4v.egzxvld1 { justify-content: flex-end; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("<div style='position: fixed; top: 10px; right: 20px;'>👔 Recruiter View (Coming Soon)</div>", unsafe_allow_html=True)
