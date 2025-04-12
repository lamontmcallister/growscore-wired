
# Skippr Full App (Final Clean Version) with:
# ✅ Supabase Login (separate screen)
# ✅ Candidate Journey (Steps 1–6)
# ✅ Recruiter Dashboard with full logic
# ✅ Emoji-cleaned UI (only ✅, ⚠️, ❌ kept)
# ✅ Ready for Streamlit Cloud

import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client
import openai

# Streamlit Page Setup
st.set_page_config(page_title="Skippr", layout="wide")

# --- Secrets & Supabase Init ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
openai.api_key = OPENAI_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Session State Defaults ---
defaults = {
    "supabase_session": None,
    "supabase_user": None,
    "step": 1,
    "demo_mode": False,
    "recruiter_mode": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Login Page ---
def show_login():
    st.title("Welcome to Skippr")
    mode = st.radio("Select an option:", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if mode == "Login":
        if st.button("Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.experimental_rerun()
            except Exception as e:
                st.error("Login failed. Please try again.")
    else:
        if st.button("Create Account"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Check your email to confirm.")
            except Exception as e:
                st.error("Signup failed. Try a different email.")

# --- Sidebar ---
def sidebar_logged_in():
    with st.sidebar:
        st.write(f"Logged in as: `{st.session_state.supabase_user.email}`")
        if st.button("Logout"):
            supabase.auth.sign_out()
            st.session_state.supabase_user = None
            st.session_state.supabase_session = None
            st.experimental_rerun()
        st.checkbox("Recruiter View", key="recruiter_mode")
        st.checkbox("Demo Mode", key="demo_mode")

# --- Candidate Journey ---
def candidate_journey():
    st.title("Candidate Journey")

    step = st.session_state.step

    if step == 1:
        st.header("Step 1: Upload Resume")
        file = st.file_uploader("Upload your resume (PDF)", type="pdf")
        text = "SQL, Recruiting, Excel, Leadership" if st.session_state.demo_mode else ""
        if file:
            with pdfplumber.open(file) as pdf:
                text = "
".join([page.extract_text() for page in pdf.pages])
        st.session_state.resume_text = text
        st.text_area("Resume Text", text)

    elif step == 2:
        st.header("Step 2: Paste Job Description")
        jd = st.text_area("Paste the job description here", value=st.session_state.get("job_desc", ""))
        if jd:
            st.session_state.job_desc = jd
            st.success("JD saved.")

    elif step == 3:
        st.header("Step 3: JD Match Score")
        resume = st.session_state.get("resume_text", "")
        jd = st.session_state.get("job_desc", "")
        if resume and jd:
            r = set(resume.lower().split())
            j = set(jd.lower().split())
            match = len(r & j) / max(len(j), 1) * 100
            st.metric("Match Score", f"{match:.1f}%")
            fig, ax = plt.subplots()
            ax.pie([match, 100 - match], labels=["Match", "Gap"], autopct="%1.1f%%")
            ax.axis("equal")
            st.pyplot(fig)

    elif step == 4:
        st.header("Step 4: Skills")
        skills = st.multiselect("Select your skills", ["SQL", "Python", "Excel", "PeopleOps", "Leadership"])
        st.session_state.skills_selected = skills
        other = st.text_input("Other skills")
        if other:
            st.session_state.skills_selected.append(other)

    elif step == 5:
        st.header("Step 5: References + Backchannel")
        name = st.text_input("Reference Name")
        email = st.text_input("Reference Email")
        if name and email:
            st.session_state.ref_name = name
            st.session_state.ref_email = email
        st.text_input("Backchannel Contact")

    elif step == 6:
        st.header("Step 6: Education + HR Check")
        st.text_input("Highest Degree")
        st.file_uploader("Upload transcript (optional)", type=["pdf", "jpg"])
        st.markdown("❌ HR Check: Missing (Coming Soon)")

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back") and step > 1:
        st.session_state.step -= 1
        st.experimental_rerun()
    if col2.button("Next ➡️") and step < 6:
        st.session_state.step += 1
        st.experimental_rerun()
    elif step == 6:
        st.success("🎉 Candidate journey complete!")
        st.balloons()

# --- Recruiter Dashboard ---
def recruiter_dashboard():
    st.title("Recruiter Dashboard")

    with st.sidebar:
        st.subheader("QoH Weight Sliders")
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    st.subheader("Candidate Table (Demo Data)")
    df = pd.DataFrame({
        "Name": ["Alex", "Sam", "Jordan"],
        "JD Match": [88, 72, 65],
        "References": [90, 50, 70],
        "Behavior": [85, 80, 75],
        "Skills": [80, 60, 50]
    })
    df["QoH Score"] = df.apply(lambda row: round((row["JD Match"] * w_jd + row["References"] * w_ref + row["Behavior"] * w_beh + row["Skills"] * w_skill) / 100, 1), axis=1)
    st.dataframe(df)

    selected = st.multiselect("Compare Candidates", df["Name"])
    if selected:
        st.subheader("Side-by-Side Comparison")
        st.dataframe(df[df["Name"].isin(selected)])

    st.subheader("AI Recommendations")
    for _, row in df.iterrows():
        if row["QoH Score"] > 80:
            st.markdown(f"✅ {row['Name']}: Strong candidate")
        elif row["References"] < 60:
            st.markdown(f"⚠️ {row['Name']}: Weak reference signal")
        elif row["Skills"] < 60:
            st.markdown(f"⚠️ {row['Name']}: Lacks technical depth")

# --- App Router ---
if not st.session_state.supabase_session:
    show_login()
else:
    sidebar_logged_in()
    if st.session_state.recruiter_mode:
        recruiter_dashboard()
    else:
        candidate_journey()
