
# Full GrowScore platform with all modules and updated login UI

import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client
import openai

st.set_page_config(page_title="Skippr", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
openai.api_key = OPENAI_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

for key, default in {"supabase_session": None, "supabase_user": None, "step": 1, "demo_mode": False}.items():
    if key not in st.session_state:
        st.session_state[key] = default

def show_login():
    st.title("Welcome to Skippr")
    mode = st.radio("Choose an option:", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if mode == "Login":
        if st.button("🔓 Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("🆕 Sign Up"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Check your email to confirm your account.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

def sidebar_logged_in():
    with st.sidebar:
        st.markdown(f"**Logged in as:** `{st.session_state.supabase_user.email}`")
        if st.button("Log Out"):
            supabase.auth.sign_out()
            st.session_state.supabase_session = None
            st.session_state.supabase_user = None
            st.experimental_rerun()
        st.checkbox("Recruiter View", key="recruiter_mode")
        st.checkbox("Demo Mode", key="demo_mode")

def recruiter_dashboard():
    st.title("Recruiter Dashboard")
    w_jd = st.slider("JD Match", 0, 100, 25)
    w_ref = st.slider("References", 0, 100, 25)
    w_beh = st.slider("Behavior", 0, 100, 25)
    w_skill = st.slider("Skills", 0, 100, 25)
    df = pd.DataFrame({
        "Name": ["Alex", "Sam", "Jordan"],
        "JD Match": [88, 72, 65],
        "References": [90, 50, 70],
        "Behavior": [85, 80, 75],
        "Skills": [80, 60, 50]
    })
    df["QoH Score"] = df.apply(lambda r: round((r["JD Match"] * w_jd + r["References"] * w_ref + r["Behavior"] * w_beh + r["Skills"] * w_skill) / 100, 1), axis=1)
    st.dataframe(df)

def candidate_journey():
    step = st.session_state.step
    if step == 1:
        st.header("Step 1: Upload Resume")
        file = st.file_uploader("Upload your resume (PDF)", type="pdf")
        text = "SQL, Recruiting, Excel, Leadership"
        if file and not st.session_state.demo_mode:
            with pdfplumber.open(file) as pdf:
                text = "
".join(p.extract_text() for p in pdf.pages)
        st.session_state.resume_text = text
        st.text_area("Resume Text", text)

    elif step == 2:
        st.header("Step 2: Paste Job Description")
        jd = st.text_area("Paste Job Description", value=st.session_state.get("job_desc", ""))
        if jd:
            st.session_state.job_desc = jd
            st.success("✅ JD saved.")

    elif step == 3:
        st.header("Step 3: JD Match")
        rt = st.session_state.get("resume_text", "")
        jd = st.session_state.get("job_desc", "")
        if rt and jd:
            r, j = set(rt.lower().split()), set(jd.lower().split())
            match = len(r & j) / max(len(j), 1) * 100
            st.metric("Match Score", f"{match:.1f}%")
            fig, ax = plt.subplots()
            ax.pie([match, 100 - match], labels=["Match", "Gap"], autopct="%1.1f%%")
            ax.axis("equal")
            st.pyplot(fig)

    elif step == 4:
        st.header("Step 4: Skills")
        skills = st.multiselect("Select Skills", ["SQL", "Python", "Excel", "PeopleOps", "Leadership"])
        st.session_state.skills_selected = skills
        other = st.text_input("Other skills:")
        if other:
            st.session_state.skills_selected.append(other)

    elif step == 5:
        st.header("Step 5: References + Backchannel")
        name = st.text_input("Reference Name")
        email = st.text_input("Reference Email")
        if name and email:
            st.session_state.ref_name = name
            st.session_state.ref_email = email
            st.success("✅ Reference saved.")
        st.text_input("Backchannel contact")

    elif step == 6:
        st.header("Step 6: Education + HR Check")
        st.text_input("Highest Degree")
        st.file_uploader("Upload Transcript (optional)", type=["pdf", "jpg"])
        st.info("🚧 HR Check Coming Soon")

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back") and step > 1:
        st.session_state.step -= 1
        st.experimental_rerun()
    if col2.button("Next ➡️") and step < 6:
        st.session_state.step += 1
        st.experimental_rerun()
    elif step == 6:
        st.success("🎉 You completed the journey!")
        st.balloons()

# === Main App Router ===
if not st.session_state.supabase_session:
    show_login()
else:
    sidebar_logged_in()
    if st.session_state.recruiter_mode:
        recruiter_dashboard()
    else:
        candidate_journey()
