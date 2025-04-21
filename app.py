import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- STYLE ---
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
            section[data-testid="stSidebar"] {
                background-color: #f9f4ef;
                border-right: 1px solid #e1dfdb;
            }
        </style>
    """, unsafe_allow_html=True)
load_custom_css()

# --- GLOBAL STATE ---
skills_pool = [
    "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
    "Communication", "Strategic Planning", "Excel", "Project Management"
]
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "step" not in st.session_state:
    st.session_state.step = 0
if "selected_profile" not in st.session_state:
    st.session_state.selected_profile = None

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

def extract_contact_info(text):
    prompt = f"From this resume, extract the full name, email, and job title. Return a Python dictionary with keys: name, email, title.\n\n{text}"
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

# --- PROFILE MANAGEMENT ---
def save_profile(email, profile_name, data):
    supabase.table("user_profiles").insert({
        "user_email": email,
        "name": profile_name,
        "data": data
    }).execute()

def load_profiles(email):
    res = supabase.table("user_profiles").select("*").eq("user_email", email).execute()
    return res.data if res else []

def candidate_profile_picker():
    email = st.session_state.supabase_user.email
    profiles = load_profiles(email)
    names = [p["name"] for p in profiles]
    selected = st.selectbox("Choose a profile to continue or create new:", ["Create New"] + names)
    if selected == "Create New":
        profile_name = st.text_input("New Profile Name")
        if profile_name and st.button("Start New Profile"):
            st.session_state.selected_profile = profile_name
            st.session_state.step = 0
    else:
        for p in profiles:
            if p["name"] == selected:
                st.session_state.selected_profile = selected
                st.session_state.step = 0
                for k, v in p["data"].items():
                    st.session_state[k] = v
                st.success(f"Loaded profile: {selected}")
                break

# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title(f"🚀 Candidate Journey — {st.session_state.selected_profile}")
    st.progress((step + 1) / 10)

    if step == 0:
        st.subheader("Step 1: Upload Resume & Contact Info")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state.resume_contact = extract_contact_info(text)
            st.success("✅ Resume parsed successfully.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.subheader("Step 2: Confirm Your Top Skills")
        selected = st.multiselect("Select your strongest skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.subheader("Step 3: Behavioral Traits")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        questions = [
            "Meets deadlines consistently",
            "Collaborates well in teams",
            "Adapts quickly to change",
            "Demonstrates leadership",
            "Communicates effectively"
        ]
        for i, q in enumerate(questions):
            res = st.radio(q, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[res]
        st.session_state.behavior_score = round((score_total / (len(questions) * 5)) * 100, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)
    elif step == 3:
        st.subheader("Step 4: References")
        traits = [
            "Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork",
            "Adaptability", "Problem Solving", "Empathy", "Initiative", "Collaboration"
        ]
        with st.expander("Reference 1"):
            st.text_input("Name", key="ref1_name")
            st.text_input("Email", key="ref1_email")
            st.selectbox("Trait to Highlight", traits, key="ref1_trait")
            st.text_area("Message (optional)", key="ref1_msg")
            if st.button("Send to Ref 1"):
                st.success(f"✅ Sent to {st.session_state.get('ref1_name')}")

        with st.expander("Reference 2"):
            st.text_input("Name", key="ref2_name")
            st.text_input("Email", key="ref2_email")
            st.selectbox("Trait to Highlight", traits, key="ref2_trait")
            st.text_area("Message (optional)", key="ref2_msg")
            if st.button("Send to Ref 2"):
                st.success(f"✅ Sent to {st.session_state.get('ref2_name')}")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.subheader("Step 5: Job Matching")
        jd1 = st.text_area("Paste Job Description 1")
        jd2 = st.text_area("Paste Job Description 2")
        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.subheader("Step 6: Quality of Hire")
        jd_scores = st.session_state.get("jd_scores", [75, 85])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        skills = len(st.session_state.get("selected_skills", [])) * 5
        qoh = round((avg_jd + ref_score + behavior + skills) / 4, 1)
        st.session_state.qoh_score = qoh
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.subheader("Step 7: Career Roadmap")
        prompt = f"Resume:\n{st.session_state.get('resume_text', '')}\n\nCreate a growth roadmap with:\n- 30-day\n- 60-day\n- 90-day\n- 6-month\n- 1-year plan."
        try:
            res = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
            roadmap = res.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Onboarding\n• 60-Day: First project\n• 90-Day: Initiative\n• 6-Month: KPIs\n• 1-Year: Promotion"
        st.markdown(roadmap)
        st.button("Back", on_click=prev_step)
        if st.button("✅ Save Profile"):
            save_profile(
                st.session_state.supabase_user.email,
                st.session_state.selected_profile,
                {k: v for k, v in st.session_state.items() if isinstance(v, (str, int, float, list))}
            )
            st.success("🎉 Profile saved!")
# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")

    with st.sidebar.expander("📊 Weight Adjustments", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Please adjust weights.")
        return

    df = pd.DataFrame([
        {
            "Candidate": "Lamont", "JD Match": 88, "Reference": 90, "Behavior": 84, "Skill": 92,
            "Gaps": "Strategic Planning", "Verified": "✅ All"
        },
        {
            "Candidate": "Jasmine", "JD Match": 82, "Reference": 78, "Behavior": 90, "Skill": 80,
            "Gaps": "Leadership", "Verified": "⚠️ Reference"
        }
    ])

    df["QoH Score"] = (
        df["JD Match"] * w_jd +
        df["Reference"] * w_ref +
        df["Behavior"] * w_beh +
        df["Skill"] * w_skill
    ) / total

    st.dataframe(df.sort_values("QoH Score", ascending=False), use_container_width=True)

# --- LOGIN UI ---
def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=350)
        st.markdown("### From Rejection to Revolution")
        st.caption("💡 I didn’t get the job. I built the platform that fixes the problem.")

    st.markdown("---")
    with st.sidebar:
        st.header("🔐 Log In / Sign Up")
        mode = st.radio("Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.success("✅ Logged in!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Registered. Check your email to confirm.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose View", ["Candidate", "Recruiter"])
    if view == "Candidate":
        candidate_profile_picker()
        if st.session_state.selected_profile:
            candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
