import streamlit as st
from supabase import create_client
import os

# Pull from secrets.toml
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]

# Connect to Supabase
supabase = create_client(url, key)

# Simple test: Query your candidates table (change to match your table)
try:
    response = supabase.table("candidates").select("*").limit(5).execute()
    st.write("✅ Supabase connection successful!")
    st.json(response.data)
except Exception as e:
    st.error("❌ Supabase connection failed:")
    st.exception(e)
