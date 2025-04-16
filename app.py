
# Skippr App – One-Page Login Sidebar Integration
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
if "show_app" not in st.session_state:
    st.session_state.show_app = False
if "is_signup" not in st.session_state:
    st.session_state.is_signup = False

def handle_auth(email, password):
    try:
        if st.session_state.is_signup:
            result = supabase.auth.sign_up({"email": email, "password": password})
        else:
            result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session = result.session
        user = result.user
        if session and user:
            st.session_state.supabase_session = session
            st.session_state.supabase_user = user
            st.session_state.show_app = True
        else:
            st.error("Login failed. Check credentials or try signing up.")
    except Exception as e:
        st.error(f"Auth error: {e}")

if not st.session_state.show_app:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### 👋 Welcome to Skippr")
        st.write("Sign in to start your Candidate Journey.")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        auth_button = st.button("Sign Up" if st.session_state.is_signup else "Log In")
        toggle_text = "Have an account? Log In" if st.session_state.is_signup else "New here? Create account"
        if st.button(toggle_text):
            st.session_state.is_signup = not st.session_state.is_signup
        if auth_button:
            handle_auth(email, password)
    with col2:
        st.markdown("## 🚀 Skippr: Verified Potential, Not Just Resumes")
        st.markdown("""
- ✅ AI-powered Quality of Hire scoring  
- 📄 Resume + JD match analysis  
- 💬 Behavior & reference verification  
- 📊 Recruiter dashboard with signal-based comparison  
        """)
        st.image("https://images.unsplash.com/photo-1519389950473-47ba0277781c", use_column_width=True)

# --- MAIN APP BELOW ---
if st.session_state.show_app:
    # Placeholder for rest of your app code – Candidate Journey, Recruiter Dashboard, etc.
    st.success("🎉 Logged in successfully! Load the Candidate Journey here.")
