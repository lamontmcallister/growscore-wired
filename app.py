st.set_page_config(page_title="Skippr", layout="wide")


# Apply custom CSS from assets
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ Custom CSS not found. Using default styling.")


import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Skippr", layout="wide")

# Inject sidebar and global styling
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            background-color: #003366 !important;
        }
        section[data-testid="stSidebar"] * {
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

# CSS fallback from file
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ Custom CSS not found. Using default styling.")

# Logo fallback
try:
    st.image("assets/logo.png", width=200)
except FileNotFoundError:
    st.warning("⚠️ Logo not found — skipping logo display.")

# Branding header HTML (in variable)
branding_html = """
<div style='text-align: center; background-color: #003366; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
    <h1 style='color: white; font-size: 36px;'>Welcome to Skippr</h1>
    <p style='color: white; font-size: 18px;'>Helping you skip the noise and land faster.</p>
</div>
"""
st.markdown(branding_html, unsafe_allow_html=True)
