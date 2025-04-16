
# Skippr App – Cleaned Homepage, Carousel, and Auth Logic
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

# Apply custom CSS if present
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ Custom CSS not found. Using default styling.")

# Load secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Session auth state
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# --- Skippr Homepage with Why Section + Carousel ---
if "show_app" not in st.session_state:
    st.session_state.show_app = False
if "carousel_index" not in st.session_state:
    st.session_state.carousel_index = 0

if not st.session_state.show_app:
    st.markdown('''
        <div style='text-align: center; padding-top: 4rem;'>
            <h1 style='color: #1A1A1A; font-size: 3rem;'>Skippr</h1>
            <h3 style='color: #333;'>Predictive Hiring Starts Here</h3>
            <p style='color: #555; font-size: 18px; max-width: 650px; margin: 2rem auto;'>
                Skippr empowers candidates to showcase verified potential — and helps recruiters find high performers faster. 
                Powered by AI. Centered on human growth.
            </p>
            <form action="" method="post">
                <button type="submit" style='margin-top: 2rem;' onclick="document.getElementById("start-btn").click()">🚀 Get Started</button>
            </form>
        </div>
    ''', unsafe_allow_html=True)

    # --- Why Skippr Section ---
    st.markdown('''
        <div style='text-align: left; max-width: 650px; margin: 3rem auto 0 auto; font-size: 17px; color: #444;'>
            <h4 style='color: #1A1A1A;'>Why Skippr?</h4>
            <ul style='list-style-type: none; padding-left: 0;'>
                <li>🔍 <strong>Smart Scoring:</strong> See your Quality of Hire (QoH) score before you apply.</li>
                <li>📈 <strong>Growth Roadmaps:</strong> Get personalized feedback and upskill plans.</li>
                <li>✅ <strong>Verified References:</strong> Build trust with recruiters from the start.</li>
                <li>💬 <strong>Transparent Insights:</strong> Understand how you're being evaluated.</li>
                <li>⚡ <strong>Real Human Potential:</strong> Get seen for your trajectory, not just your resume.</li>
            </ul>
        </div>
    ''', unsafe_allow_html=True)

    # --- Carousel Section ---
    carousel_slides = [
        "🚀 <strong>See Your Score Before You Apply:</strong><br> Understand your job fit with a verified Quality of Hire (QoH) score.",
        "📊 <strong>Track Skill Gaps. Grow Fast.</strong><br> Get smart, personalized growth plans — powered by AI.",
        "🤝 <strong>Verified References = Instant Credibility</strong><br> Trusted signals that boost recruiter confidence.",
        "🎯 <strong>Built to Help You Skip the Line</strong><br> Go from overlooked to in-demand with Skippr."
    ]

    current_slide = st.session_state.carousel_index
    st.markdown(f"<div style='text-align: center; font-size: 18px; color: #333; margin-top: 3rem;'><p>{carousel_slides[current_slide]}</p></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️", key="prev_slide") and st.session_state.carousel_index > 0:
            st.session_state.carousel_index -= 1
    with col3:
        if st.button("▶️", key="next_slide") and st.session_state.carousel_index < len(carousel_slides) - 1:
            st.session_state.carousel_index += 1

    if st.button("🚀 Get Started", key="start-btn"):
        st.session_state.show_app = True

    st.stop()

# --- Sidebar (if logged in) ---
with st.sidebar:
    if st.session_state.supabase_user:
        st.write(f"Welcome, {st.session_state.supabase_user['email']}")
