
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

# Inject custom CSS from assets
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ Custom CSS not found. Using default Streamlit styling.")


# Branding Header
st.image("assets/logo.png", width=120)
st.markdown("""
<div style='text-align: center; margin-top: -10px;'>
    <h1 style='color: white;'>Welcome to Skippr</h1>
    <p style='color: #CCCCCC; font-size: 18px;'>🧭 Helping you skip the noise and land faster.</p>
</div>
""", unsafe_allow_html=True)

# Load secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Auth state
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# Login UI
with st.sidebar:
    st.header("🧭 Candidate Login")
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
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("🆕 Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check email for verification.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

if not st.session_state.supabase_session:
    st.info("🧭 Please sign in to continue.")
    st.stop()

# ---- Rest of your app logic continues below this ----
# (e.g., resume upload, JD match, reference flow, etc.)
