import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Segoe UI', sans-serif;
            padding: 0rem !important;
        }
        h1, h2, h3 {
            font-weight: 600 !important;
            margin-bottom: 0.5rem;
        }
        div.stButton > button {
            background-color: #ff6a00;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0.5rem 1.2rem;
            font-weight: 600;
            font-size: 1rem;
            margin-top: 0.5rem;
        }
        .stSlider > div {
            padding-top: 0.5rem;
        }
        section[data-testid="stSidebar"] {
            background-color: #f9f4ef;
            border-right: 1px solid #e1dfdb;
        }
        .markdown-block {
            background-color: #f8f8f8;
            padding: 1rem 1.5rem;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE DEFAULTS ---
for k in ["supabase_session", "supabase_user", "step", "profile_id", "profile_data"]:
    if k not in st.session_state:
        if k == "step":
            st.session_state[k] = 0
        elif k == "profile_data":
            st.session_state[k] = {}
        else:
            st.session_state[k] = None

# --- GPT HELPERS ---
def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\n{text}\nReturn as a Python list."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return ["Python", "SQL", "Excel"]

# --- PROFILE MANAGEMENT ---
def load_profiles():
    user_id = st.session_state.supabase_user.id
    res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    return res.data if res.data else []

def save_profile_data(data):
    if st.session_state.profile_id:
        supabase.table("profiles").update({"data": data}).eq("id", st.session_state.profile_id).execute()

def create_new_profile(name):
    user_id = st.session_state.supabase_user.id
    res = supabase.table("profiles").insert({"user_id": user_id, "name": name, "data": {}}).execute()
    st.session_state.profile_id = res.data[0]['id']
    st.session_state.profile_data = {}

# --- LOGIN UI ---
def login_ui():
    st.markdown("##")
    st.markdown("### Empower Your Career Journey")
    st.caption("💡 Skippr: From Rejection to Revolution — Helping you and recruiters match better, faster.")
    st.markdown("---")
    with st.sidebar:
        st.header("🔐 Log In or Create Account")
        mode = st.radio("Choose Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# --- PROFILE SELECTION ---
def profile_selector():
    profiles = load_profiles()
    profile_names = [p["name"] for p in profiles]
    selected = st.selectbox("Select Profile or Create New", ["Create New"] + profile_names)
    if selected == "Create New":
        new_name = st.text_input("New Profile Name")
        if st.button("Create Profile") and new_name:
            create_new_profile(new_name)
            st.experimental_rerun()
    else:
        st.session_state.profile_id = [p["id"] for p in profiles if p["name"] == selected][0]
        st.session_state.profile_data = [p["data"] for p in profiles if p["name"] == selected][0]
        st.success(f"Loaded profile: {selected}")

# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)
    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Contact Info")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Growth Roadmap")
        roadmap = "• 30-Day: Onboard\n• 60-Day: Deliver small win\n• 90-Day: Lead initiative\n• 6-Month: Strategic growth\n• 1-Year: Prepare for promotion"
        st.markdown(roadmap)
        st.success("🎉 Complete!")
        save_profile_data({
            "name": st.session_state.get("cand_name", ""),
            "skills": st.session_state.get("resume_skills", []),
            "resume": st.session_state.get("resume_text", ""),
            "roadmap": roadmap
        })

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    st.write("This is your Recruiter Dashboard. Candidate data here can be customized.")
    st.dataframe(pd.DataFrame(load_profiles()))

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        if not st.session_state.profile_id:
            profile_selector()
        else:
            candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
