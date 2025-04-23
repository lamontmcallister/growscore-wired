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
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; padding: 0rem !important; }
            h1, h2, h3 { font-weight: 600 !important; margin-bottom: 0.5rem; }
            div.stButton > button { background-color: #ff6a00; color: white; border: none; border-radius: 6px; padding: 0.5rem 1.2rem; font-weight: 600; font-size: 1rem; margin-top: 0.5rem; }
            .stSlider > div { padding-top: 0.5rem; }
            section[data-testid="stSidebar"] { background-color: #f9f4ef; border-right: 1px solid #e1dfdb; }
            .markdown-block { background-color: #f8f8f8; padding: 1rem 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 1rem; }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION INIT ---
for k in ["supabase_session", "supabase_user", "step", "active_profile"]:
    if k not in st.session_state:
        st.session_state[k] = 0 if k == "step" else None

# --- UTILITIES ---
skills_pool = ["Python", "SQL", "Leadership", "Data Analysis", "Machine Learning", "Communication", "Strategic Planning", "Excel", "Project Management"]

def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\n{text}\nReturn as a Python list."
    try:
        res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0.3)
        return ast.literal_eval(res.choices[0].message.content.strip())
    except: return ["Python", "SQL", "Excel"]

def extract_contact_info(text):
    prompt = f"From this resume, extract the full name, email, and job title. Return as {{'name':'','email':'','title':''}}.\n\n{text}"
    try:
        res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return ast.literal_eval(res.choices[0].message.content.strip())
    except: return {"name": "", "email": "", "title": ""}

def match_resume_to_jds(resume_text, jd_texts):
    prompt = f"Given this resume:\n{resume_text}\n\nMatch semantically to the following JDs:\n"
    for i, jd in enumerate(jd_texts):
        prompt += f"\nJD {i+1}:\n{jd}\n"
    prompt += "\nReturn a list of match scores, e.g. [82, 76]"
    try:
        res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return [np.random.randint(70, 90) for _ in jd_texts]

def calculate_qoh_score(skill_count, ref, behav, jd_scores):
    avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
    skills = skill_count * 5
    final = round((skills + ref + behav + avg_jd) / 4, 1)
    return final, {"Skills": skills, "References": ref, "Behavior": behav, "JD Match": avg_jd}
# --- LOGIN ---
def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=350)
        st.markdown("### From Rejection to Revolution")
        st.caption("💡 I didn’t get the job. I built the platform that fixes the problem.")
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
                st.success("✅ Logged in successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# --- PROFILE SELECTOR (ONE TIME) ---
def profile_selector():
    st.markdown("### 👤 Select or Create a Candidate Profile")
    user_id = st.session_state.supabase_user.id
    profiles = supabase.table("profiles").select("*").eq("user_id", user_id).execute().data
    profile_names = [p["name"] for p in profiles]
    selected = st.selectbox("Select Profile", profile_names + ["Create New"])
    if selected == "Create New":
        new_name = st.text_input("New Profile Name")
        if st.button("Create Profile") and new_name:
            supabase.table("profiles").insert({"user_id": user_id, "name": new_name, "data": {}}).execute()
            st.session_state.active_profile = new_name
            st.success(f"Created & selected profile: {new_name}")
    else:
        st.session_state.active_profile = selected
        st.success(f"Loaded profile: {selected}")

# --- CANDIDATE JOURNEY (Steps 1-10 logic same as before, adjusted for save/load support) ---

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚 Adjust Quality of Hire Weights", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)
    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Adjust sliders to see candidate scores.")
        return
    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Reference": 90, "Behavior": 84, "Skill": 92, "Gaps": "Strategic Planning"},
        {"Candidate": "Jasmine", "JD Match": 82, "Reference": 78, "Behavior": 90, "Skill": 80, "Gaps": "Leadership"},
        {"Candidate": "Andre", "JD Match": 75, "Reference": 65, "Behavior": 70, "Skill": 78, "Gaps": "Communication"}
    ])
    df["QoH Score"] = (df["JD Match"] * w_jd + df["Reference"] * w_ref + df["Behavior"] * w_beh + df["Skill"] * w_skill) / total
    df = df.sort_values("QoH Score", ascending=False)
    st.subheader("📊 Candidate Comparison Table")
    st.dataframe(df[["Candidate", "JD Match", "Reference", "Behavior", "Skill", "QoH Score", "Gaps"]], use_container_width=True)
    st.markdown("---")
    st.subheader("🔍 AI Recommendations")
    for _, row in df.iterrows():
        score = row["QoH Score"]
        if score >= 90:
            st.success(f"✅ {row['Candidate']}: Strong hire.")
        elif row["Reference"] < 75:
            st.warning(f"⚠️ {row['Candidate']}: Weak reference.")
        elif row["Skill"] < 80:
            st.info(f"ℹ️ {row['Candidate']}: Gap in **{row['Gaps']}**.")
        else:
            st.write(f"{row['Candidate']}: Interview-ready.")

# --- ROUTING ---
if st.session_state.supabase_user:
    if st.session_state.active_profile:
        candidate_journey()
    else:
        profile_selector()
else:
    login_ui()
