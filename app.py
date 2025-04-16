import streamlit as st
import pandas as pd

st.set_page_config(page_title="Skippr", layout="wide")

if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "show_app" not in st.session_state:
    st.session_state.show_app = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Candidate"

# Sidebar login layout
with st.sidebar:
    st.image("https://i.ibb.co/tPDqFQF/skippr-logo-dark.png", width=120)
    st.header("🔐 Log in to Skippr")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        st.session_state.supabase_user = {"email": email}
        st.session_state.show_app = True

# Hero image and mission
if not st.session_state.show_app:
    st.markdown("""
        <div style='text-align: center; padding-top: 2rem;'>
            <h1 style='font-size: 2.5em;'>🚀 Welcome to Skippr</h1>
            <h3 style='color: gray;'>Predictive Hiring. Verified Potential.</h3>
            <p style='max-width: 700px; margin: auto; padding-top: 1rem;'>
                We believe great candidates shouldn't be overlooked because of resume formatting or job titles.
                Skippr helps you stand out with verified skills, reference-backed insights, and role-specific matching
                that goes beyond keywords. Powered by AI. Backed by humans.
            </p>
            <img src='https://images.unsplash.com/photo-1600195077073-3c9b46be6405?auto=format&fit=crop&w=1400&q=80' width='80%' style='margin-top: 2rem; border-radius: 12px;'/>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

