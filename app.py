# Skippr MVP Reboot — Part 1: Fullscreen Login + Clean Routing

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
        <p>Login or create an account to begin your personalized candidate journey.</p>
    </div>
    """, unsafe_allow_html=True)

    auth_mode = st.radio("Action", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

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
    else:
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
