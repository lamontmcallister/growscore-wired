
import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ast
from datetime import datetime
from PIL import Image

from supabase import create_client, Client

# Load secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Inject CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("assets/style.css")

# Auth state
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# Branding sidebar
with st.sidebar:
    st.image("assets/logo.png", width=150)
    st.markdown("## Welcome to Skippr 🧭")
    st.markdown("Helping you skip the noise and land faster.")
    st.markdown("---")
    st.markdown("👋 **Skip the guesswork**")
    st.markdown("Let hiring teams see your real value with verified performance, behavior, and skill signals.")
    st.markdown("🧭 **Get started by logging in or creating an account.**")

    st.header("👤 Login / Register")
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
    st.stop()
