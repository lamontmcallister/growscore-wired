
import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import datetime

# Page config and custom styling
st.set_page_config(page_title="Skippr", layout="wide")

st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Segoe UI', sans-serif;
            background-color: #f5f9fc;
        }
        .main {
            background-color: #ffffff;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        }
        .stTextInput > label, .stTextArea > label {
            font-weight: bold;
            color: #0e1117;
        }
        .stButton > button {
            background-color: #007BFF;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 5px;
        }
        .stButton > button:hover {
            background-color: #0056b3;
        }
        .header {
            text-align: center;
            font-size: 2.2rem;
            font-weight: bold;
            color: #0e1117;
            padding-top: 2rem;
        }
    </style>
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

# Redesigned Login UI
if not st.session_state.supabase_session:
    st.markdown('<div class="header">🚀 Welcome to Skippr</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown("### 👤 Sign In or Register")
        auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
        email = st.text_input("Email", placeholder="you@domain.com")
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
                    st.success("✅ Account created. Check email for verification.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")
    st.stop()

# Placeholder for rest of app
st.success("🔥 Login successful – let’s build the rest of Skippr!")
