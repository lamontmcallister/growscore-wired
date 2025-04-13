
# Skippr MVP — Full App (Login + Candidate Journey + Recruiter Dashboard)
import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client
import openai

# Config
st.set_page_config(page_title="Skippr", layout="wide")

# Load CSS
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except:
    pass

# Supabase & OpenAI
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Initialize Session State
defaults = {
    "supabase_user": None,
    "supabase_session": None,
    "step": 1,
    "resume_text": "",
    "job_desc": "",
    "skills": [],
    "match_score": 0,
    "demo_mode": False,
    "recruiter_mode": False
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Login View
def show_login():
    st.markdown("### 🔐 Welcome to Skippr")
    auth_mode = st.radio("Choose:", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if auth_mode == "Login":
        if st.button("Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = result.user
                st.session_state.supabase_session = result.session
                st.rerun()
            except Exception as e:
                st.error("Login failed.")
    else:
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created. Please check email to confirm.")
            except Exception as e:
                st.error("Signup failed.")

# Sidebar after login
def sidebar_logged_in():
    with st.sidebar:
        st.write(f"📧 Logged in as: {st.session_state.supabase_user.email}")
        if st.button("Logout"):
            supabase.auth.sign_out()
            for key in defaults:
                st.session_state[key] = defaults[key]
            st.rerun()
        st.checkbox("Recruiter View", key="recruiter_mode")
        st.checkbox("Demo Mode", key="demo_mode")

# Candidate Journey Steps
def step_1():
    st.subheader("Step 1: Upload Resume")
    file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    if file or st.session_state.demo_mode:
        resume_text = "Experienced recruiter with data analysis and talent ops." if st.session_state.demo_mode else ""
        if file:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    resume_text += page.extract_text()
        st.session_state.resume_text = resume_text
        st.text_area("Parsed Resume", resume_text, height=200)
        st.success("✅ Resume loaded.")
    if st.button("Next"):
        st.session_state.step += 1
        st.rerun()

def step_2():
    st.subheader("Step 2: Paste Job Description")
    jd = st.text_area("Paste JD", st.session_state.job_desc or "")
    st.session_state.job_desc = jd
    if st.button("Next"):
        st.session_state.step += 1
        st.rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.rerun()

def step_3():
    st.subheader("Step 3: JD Match Score")
    r_words = set(st.session_state.resume_text.lower().split())
    j_words = set(st.session_state.job_desc.lower().split())
    overlap = r_words.intersection(j_words)
    score = len(overlap) / max(len(j_words), 1) * 100
    st.session_state.match_score = score
    st.metric("Match Score", f"{score:.1f}%")
    fig, ax = plt.subplots()
    ax.pie([score, 100 - score], labels=["Match", "Gap"], autopct="%1.1f%%")
    ax.axis("equal")
    st.pyplot(fig)
    if st.button("Next"):
        st.session_state.step += 1
        st.rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.rerun()

def step_4():
    st.subheader("Step 4: Skill Selection")
    skills = ["Python", "SQL", "Recruiting Ops", "Data Viz", "ATS Systems"]
    chosen = st.multiselect("Your Skills:", skills, default=skills[:2] if st.session_state.demo_mode else [])
    st.session_state.skills = chosen
    if st.button("Next"):
        st.session_state.step += 1
        st.rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.rerun()

def step_5():
    st.subheader("Step 5: References")
    st.text_input("Reference Name")
    st.text_input("Reference Email")
    st.text_input("Backchannel Contact (Optional)")
    st.info("🚧 Reference email verification coming soon.")
    if st.button("Next"):
        st.session_state.step += 1
        st.rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.rerun()

def step_6():
    st.subheader("Step 6: Education + HR Check")
    st.text_input("Highest Degree")
    st.text_input("Institution")
    st.info("🚧 HR verification coming soon.")
    if st.button("Next"):
        st.session_state.step += 1
        st.rerun()
    if st.button("Back"):
        st.session_state.step -= 1
        st.rerun()

def step_7():
    st.subheader("Step 7: QoH Score")
    m = st.session_state.match_score
    s = len(st.session_state.skills) * 10
    r = 20
    e = 10
    qoh = (m + s + r + e) / 4
    st.metric("QoH Score", f"{qoh:.1f}")
    st.progress(int(qoh))
    st.success("🎉 Journey Complete")
    if st.button("Back"):
        st.session_state.step -= 1
        st.rerun()

# Recruiter Dashboard
def show_recruiter():
    st.title("Recruiter Dashboard")
    st.subheader("Candidate Comparison")
    candidates = pd.DataFrame({
        "Candidate": ["You", "Demo User"],
        "QoH": [st.session_state.match_score + 30, 72.5],
        "Match %": [st.session_state.match_score, 68],
        "Skills Gap": ["2 missing", "3 missing"]
    })
    st.dataframe(candidates, use_container_width=True)
    st.subheader("Adjust QoH Weights")
    st.slider("Match", 0, 100, 25)
    st.slider("Skills", 0, 100, 25)
    st.slider("References", 0, 100, 25)
    st.slider("Education", 0, 100, 25)
    st.markdown("✅ Candidate A looks strong.
⚠️ Candidate B needs coaching.")

# Main Routing
if not st.session_state.supabase_session:
    show_login()
else:
    sidebar_logged_in()
    if st.session_state.recruiter_mode:
        show_recruiter()
    else:
        step = st.session_state.step
        steps = {
            1: step_1,
            2: step_2,
            3: step_3,
            4: step_4,
            5: step_5,
            6: step_6,
            7: step_7
        }
        steps[step]()
