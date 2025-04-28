import streamlit as st
import openai
import pdfplumber
import pandas as pd
import ast
import json
from datetime import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="GrowScore Polished", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- AUTH ---
def login_section():
    st.sidebar.title("Login / Signup")
    auth_mode = st.sidebar.radio("Choose", ["Login", "Sign Up"])
    if auth_mode == "Sign Up":
        email = st.sidebar.text_input("Email", key="signup_email")
        password = st.sidebar.text_input("Password", type="password", key="signup_password")
        if st.sidebar.button("Register"):
            try:
                user = supabase.auth.sign_up({"email": email, "password": password})
                st.sidebar.success("Account created! Please check your email for verification.")
            except Exception as e:
                st.sidebar.error(f"Signup error: {e}")
    if auth_mode == "Login":
        email = st.sidebar.text_input("Email", key="login_email")
        password = st.sidebar.text_input("Password", type="password", key="login_password")
        if st.sidebar.button("Login Now"):
            try:
                user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = user
                st.sidebar.success(f"Welcome {email}!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Login error: {e}")
    if st.session_state.get("supabase_user"):
        if st.sidebar.button("Log Out"):
            st.session_state.supabase_user = None
            st.rerun()

# --- PROFILE MANAGEMENT --- (UNCHANGED)
def profile_management():
    st.title("👤 Profile Management")
    user_email = st.session_state.supabase_user.user.email
    try:
        profiles = supabase.table("profiles").select("*").eq("user_email", user_email).execute()
    except Exception as e:
        st.error(f"❌ Supabase query error: {e}")
        st.stop()

    profile_names = [p["name"] for p in profiles.data] if profiles.data else []
    st.write("Choose a profile or create a new one:")
    if profile_names:
        selected = st.selectbox("Select Existing Profile", ["Create New"] + profile_names)
    else:
        selected = "Create New"
        st.info("No profiles found. Create a new one.")
    if selected == "Create New":
        new_name = st.text_input("Enter New Profile Name")
        if st.button("Start with New Profile") and new_name:
            st.session_state.active_profile = new_name
            st.session_state.step = 0
            st.rerun()
    elif selected:
        st.session_state.active_profile = selected
        st.session_state.step = 0
        if st.button(f"Edit Profile: {selected}"):
            st.rerun()

# --- POLISHED CANDIDATE JOURNEY UI ---
def candidate_journey():
    step = st.session_state.get("step", 0)

    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.header(f"🚀 Candidate Journey – Profile: {st.session_state.active_profile}")
    st.progress((step + 1) / 8)

    if step == 0:
        st.subheader("📄 Step 1: Contact Info + Resume Upload")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.success("✅ Resume parsed.")
        st.button("Next ➡️", on_click=next_step)

    elif step == 1:
        st.subheader("🛠 Step 2: Skills + Behavior Survey")
        skills_pool = ["Python", "SQL", "Leadership", "Data Analysis", "Communication"]
        selected = st.multiselect("Select your skills:", skills_pool)
        st.session_state.selected_skills = selected

        st.markdown("#### Behavior Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        for i, q in enumerate([
            "Meets deadlines consistently",
            "Collaborates well in teams",
            "Adapts quickly to change",
            "Demonstrates leadership",
            "Communicates effectively"
        ]):
            response = st.radio(q, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        st.session_state.behavior_score = round((score_total / 25) * 100, 1)

        st.button("⬅️ Back", on_click=prev_step)
        st.button("Next ➡️", on_click=next_step)

# --- POLISHED RECRUITER DASHBOARD UI ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚 Customize QoH Weights", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total_weight = max(1, w_jd + w_ref + w_beh + w_skill)

    try:
        profiles = supabase.table("profiles").select("*").execute()
        data = profiles.data if profiles.data else []
    except Exception as e:
        st.error(f"❌ Could not fetch profiles: {e}")
        return

    if data:
        df = pd.DataFrame(data)
        df["skills_score"] = df["selected_skills"].apply(lambda x: len(x) * 5 if isinstance(x, list) else 0)
        df["avg_jd"] = df["jd_scores"].apply(lambda x: sum(x)/len(x) if isinstance(x, list) and len(x) > 0 else 0)
        df["QoH"] = (
            df["avg_jd"] * w_jd +
            df["skills_score"] * w_skill +
            df["behavior_score"] * w_beh +
            90 * w_ref
        ) / total_weight
        df = df.sort_values("QoH", ascending=False)

        st.metric("📊 Average QoH", f"{df['QoH'].mean():.1f}/100")
        st.dataframe(df[["name", "job_title", "avg_jd", "skills_score", "behavior_score", "QoH"]])
    else:
        st.info("No profiles found.")

# --- MAIN ---
def main():
    login_section()
    if st.session_state.get("supabase_user"):
        mode = st.sidebar.selectbox("Mode", ["Candidate", "Recruiter"])
        if mode == "Candidate":
            if "active_profile" not in st.session_state:
                profile_management()
            else:
                candidate_journey()
        elif mode == "Recruiter":
            recruiter_dashboard()
    else:
        st.warning("Please log in to access GrowScore features.")

if __name__ == "__main__":
    main()
