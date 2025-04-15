import streamlit as st
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Skippr", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Session state initialization
for key, default in {
    "supabase_user": None,
    "supabase_session": None,
    "profile_id": None,
    "page": "home"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Homepage Display ---
if st.session_state.page == "home":
    st.markdown("## Welcome to Skippr 🚀")
    st.markdown("Predictive, verified, human-centered hiring — powered by AI.")
    st.markdown("Skippr helps candidates showcase their true potential, and helps recruiters focus on what matters.")
    st.markdown(" ")
    st.markdown(" ")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state.page = "app"

def render_full_app():
    
    
    # Apply custom CSS from assets
# --- App Rendering ---
if st.session_state.page == "app":
    render_full_app()
