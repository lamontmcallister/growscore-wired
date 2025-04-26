import streamlit as st
import openai
import pdfplumber
import pandas as pd
import ast
import numpy as np
from datetime import datetime
from supabase import create_client, Client



st.set_page_config(page_title="GrowScore Enhanced", layout="wide")
# --- CONFIG ---

st.set_page_config(page_title="GrowScore Enhanced", layout="wide")

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
                st.experimental_rerun()
            except Exception as e:
                st.sidebar.error(f"Login error: {e}")
    if st.session_state.get("supabase_user"):
        if st.sidebar.button("Log Out"):
            st.session_state.supabase_user = None
            st.experimental_rerun()

login_section()
if not st.session_state.get("supabase_user"):
    st.warning("Please log in to access GrowScore features.")
    st.stop()

st.set_page_config(page_title="Skippr", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- STYLING ---
def load_custom_css():
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
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION SETUP ---
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "step" not in st.session_state:
    st.session_state.step = 0

skills_pool = [
    "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
    "Communication", "Strategic Planning", "Excel", "Project Management"
]

# --- HELPERS ---
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

def extract_contact_info(text):
    prompt = f"From this resume, extract full name, email, and target job title. Return as a dictionary."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return {"name": "", "email": "", "title": ""}

def match_resume_to_jds(resume_text, jd_texts):
    prompt = f"Given this resume:\n{resume_text}\n\nMatch semantically to the following JDs:\n"
    for i, jd in enumerate(jd_texts):
        prompt += f"\nJD {i+1}:\n{jd}\n"
    prompt += "\nReturn a list of match scores, e.g. [82, 76]"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return [np.random.randint(70, 90) for _ in jd_texts]

# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Info")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state.resume_contact = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 🔍 Step 2: Skill Selection")
        selected = st.multiselect("Highlight your top skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.caption("How do you show up in a team or organization?")
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
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        traits = ["Leadership", "Communication", "Teamwork", "Initiative", "Adaptability"]
        for idx in [1, 2]:
            with st.expander(f"Reference {idx}"):
                st.text_input("Name", key=f"ref{idx}_name")
                st.text_input("Email", key=f"ref{idx}_email")
                st.selectbox("Trait", traits, key=f"ref{idx}_trait")
                st.text_area("Message to Referee (optional)", key=f"ref{idx}_msg")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Optional Backchannel")
        st.text_input("Name")
        st.text_input("Email")
        st.text_area("Message or Feedback Request")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Grad Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 🏢 Step 7: HR Verification")
        st.text_input("Company")
        st.text_input("Manager")
        st.text_input("HR Email")
        st.checkbox("I authorize verification")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: Job Match")
        jd1 = st.text_area("Paste Job Description 1")
        jd2 = st.text_area("Paste Job Description 2")
        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire")
        jd_scores = st.session_state.get("jd_scores", [80, 85])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        ref = 90
        qoh = round((skills + behavior + ref + avg_jd) / 4, 1)
        st.metric("📈 Quality of Hire (QoH)", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Growth Roadmap")
        prompt = f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\nGenerate a growth roadmap:\n- 30-day\n- 60-day\n- 90-day\n- 6-month\n- 1-year"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
            st.markdown(response.choices[0].message.content.strip())
        except:
            st.markdown("• 30-Day: Get oriented\n• 60-Day: Deliver project\n• 90-Day: Lead initiative\n• 6-Month: Exceed KPIs\n• 1-Year: Level up")
        st.success("🎉 Complete!")
        st.button("Back", on_click=prev_step)

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚 Customize Weights", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)
    total = w_jd + w_ref + w_beh + w_skill
    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Reference": 90, "Behavior": 84, "Skill": 92},
        {"Candidate": "Jasmine", "JD Match": 82, "Reference": 78, "Behavior": 90, "Skill": 80},
        {"Candidate": "Andre", "JD Match": 75, "Reference": 65, "Behavior": 70, "Skill": 78}
    ])
    df["QoH"] = (df["JD Match"] * w_jd + df["Reference"] * w_ref + df["Behavior"] * w_beh + df["Skill"] * w_skill) / total
    df = df.sort_values("QoH", ascending=False)
    st.dataframe(df)

# --- LOGIN UI ---
def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 💬 Mission Statement")
        st.markdown("""
        <div style='text-align: center; font-size: 20px; font-weight: 500; line-height: 1.5;'>
            <em>From Rejection to Revolution.</em><br>
            Skippr exists to restore dignity in hiring—<br>
            empowering talent with data, coaching, and visibility,<br>
            while giving recruiters the signal they’ve always needed:<br>
            <strong>Verified Quality of Hire</strong>, before the first interview.
        </div>
        """, unsafe_allow_html=True)

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
                st.success("✅ Logged in successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email for verification.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
