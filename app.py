# Skippr Full App (Upgraded best.py) – Candidate Journey + Recruiter Dashboard

import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client
import openai

st.set_page_config(page_title="Skippr", layout="wide")

# === Supabase Setup ===
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
openai.api_key = OPENAI_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Session State Defaults ===
for k, v in {"supabase_session": None, "supabase_user": None, "current_page": "login", "step": 1, "demo_mode": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# === Login Page ===
def show_login():
    st.title("Welcome to Skippr")
    mode = st.radio("Action", ["Login", "Sign Up"], horizontal=True)
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
                st.success("✅ Check your inbox to verify.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# === Sidebar ===
def sidebar_logged_in():
    with st.sidebar:
        st.markdown(f"**Logged in as:** `{st.session_state.supabase_user.email}`")
        if st.button("Log Out"):
            supabase.auth.sign_out()
            for k in ["supabase_session", "supabase_user"]:
                st.session_state[k] = None
            st.experimental_rerun()
        st.checkbox("Recruiter View", key="recruiter_mode")
        st.checkbox("Demo Mode", key="demo_mode")

# === Recruiter Dashboard ===
def recruiter_dashboard():
    st.title("🧑‍💼 Recruiter Dashboard")

    with st.sidebar.expander("🎚️ QoH Weight Sliders", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    st.markdown("### Candidate Table (Demo Data)")
    df = pd.DataFrame({
        "Name": ["Alex", "Sam", "Jordan"],
        "JD Match": [88, 72, 65],
        "References": [90, 50, 70],
        "Behavior": [85, 80, 75],
        "Skills": [80, 60, 50]
    })

    def calc_qoh(row):
        return round((row["JD Match"] * w_jd + row["References"] * w_ref + row["Behavior"] * w_beh + row["Skills"] * w_skill) / 100, 1)

    df["QoH Score"] = df.apply(calc_qoh, axis=1)
    st.dataframe(df)

    selected = st.multiselect("Compare Candidates", df["Name"])
    if selected:
        st.subheader("🆚 Side-by-Side Comparison")
        st.dataframe(df[df["Name"].isin(selected)])

    st.subheader("🧠 AI Recommendations")
    for _, row in df.iterrows():
        if row["QoH Score"] > 80:
            st.success(f"{row['Name']} ✅ Strong candidate. Consider fast-tracking.")
        elif row["References"] < 60:
            st.warning(f"{row['Name']} ⚠️ Weak reference signal. May need deeper check.")
        elif row["Skills"] < 60:
            st.info(f"{row['Name']} may need coaching for a better role fit.")

# === Candidate Journey ===
def candidate_journey():
    step = st.session_state.step
    if step == 1:
        st.header("Step 1: Upload Resume")
        file = st.file_uploader("Upload Resume (PDF)", type="pdf")
        if file or st.session_state.demo_mode:
            text = "SQL, Recruiting, Excel, Leadership" if st.session_state.demo_mode else ""
            if file:
                with pdfplumber.open(file) as pdf:
                    text = "
".join(p.extract_text() for p in pdf.pages)
            st.session_state.resume_text = text
            st.text_area("Resume Text", text)

    elif step == 2:
        st.header("Step 2: Paste Job Description")
        jd = st.text_area("Paste JD", value=st.session_state.get("job_desc", ""))
        if jd:
            st.session_state.job_desc = jd
            st.success("✅ JD saved.")

    elif step == 3:
        st.header("Step 3: JD Match")
        resume = st.session_state.get("resume_text", "")
        jd = st.session_state.get("job_desc", "")
        if resume and jd:
            r = set(resume.lower().split())
            j = set(jd.lower().split())
            match = len(r & j) / max(len(j), 1) * 100
            st.session_state.match_score = match
            st.metric("Match Score", f"{match:.1f}%")
            fig, ax = plt.subplots()
            ax.pie([match, 100 - match], labels=["Match", "Gap"], autopct="%1.1f%%")
            ax.axis("equal")
            st.pyplot(fig)

    elif step == 4:
        st.header("Step 4: Skills")
        options = ["SQL", "Python", "Excel", "Leadership"]
        skills = st.multiselect("Select Skills", options, default=options[:2] if st.session_state.demo_mode else [])
        st.session_state.skills_selected = skills
        extra = st.text_input("Other skills:")
        if extra:
            st.session_state.skills_selected.append(extra)

    elif step == 5:
        st.header("Step 5: References + Backchannel")
        name = st.text_input("Reference Name")
        email = st.text_input("Reference Email")
        if name and email:
            st.session_state.ref_name = name
            st.session_state.ref_email = email
            st.success("✅ Reference info saved.")
            st.button("Send Request (Coming Soon)", disabled=True)
        bc = st.text_input("Backchannel contact")
        if bc:
            st.session_state.backchannel = bc

    elif step == 6:
        st.header("Step 6: Education + HR Check")
        degree = st.text_input("Highest Degree")
        st.session_state.education = degree
        st.file_uploader("Upload Transcript", type=["pdf", "jpg"])
        st.markdown("🚧 HR Verification (Coming Soon)")

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back") and step > 1:
        st.session_state.step -= 1
        st.experimental_rerun()
    if col2.button("Next ➡️") and step < 6:
        st.session_state.step += 1
        st.experimental_rerun()
    elif step == 6:
        st.success("🎉 You completed the candidate journey!")
        st.balloons()

# === App Router ===
if not st.session_state.supabase_session:
    show_login()
else:
    sidebar_logged_in()
    if st.session_state.recruiter_mode:
        recruiter_dashboard()
    else:
        candidate_journey()
