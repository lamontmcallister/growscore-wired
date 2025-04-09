
import streamlit as st
import os
import openai
import pdfplumber
from supabase import create_client, Client

# ---- Page setup ----
st.set_page_config(page_title="Skippr", layout="wide")

# ---- Load styling with fallback ----
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.markdown("<!-- No custom CSS found -->", unsafe_allow_html=True)

# ---- Show logo with fallback ----
try:
    st.image("assets/logo.png", width=160)
except FileNotFoundError:
    st.markdown("### Skippr")

# ---- Auth Setup ----
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# ---- Sidebar Login ----
with st.sidebar:
    st.header("Candidate Login")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if auth_mode == "Login":
        if st.button("Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.success(f"Logged in as {email}")
            except Exception as e:
                st.error("Login failed.")
    else:
        if st.button("Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created. Check email to confirm.")
            except Exception as e:
                st.error("Signup failed.")

# ---- Require login to continue ----
if not st.session_state.supabase_session:
    st.stop()

# ---- Candidate Journey ----
st.header("Candidate Journey")

st.info("Upload your resume below to begin.")

uploaded_resume = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
resume_text = ""
if uploaded_resume:
    with pdfplumber.open(uploaded_resume) as pdf:
        resume_text = " ".join(page.extract_text() for page in pdf.pages if page.extract_text())

    st.success("Resume uploaded successfully!")

    if st.button("Extract skills from resume"):
        skill_prompt = f"Extract 8–12 professional skills from this resume:

{resume_text[:2000]}"
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": skill_prompt}],
            temperature=0.3
        )
        st.subheader("Extracted Skills:")
        st.write(response.choices[0].message.content)
