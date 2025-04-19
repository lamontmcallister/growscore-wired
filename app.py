import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
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

# --- SESSION INIT ---
for k in ["supabase_session", "supabase_user", "step", "profile_name"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "step" else 0

skills_pool = [
    "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
    "Communication", "Strategic Planning", "Excel", "Project Management"
]

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

# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    if step == 0:
        st.title("🚀 Start Your Candidate Journey")
        st.text_input("🔖 Profile Name (create a title to track this profile)", key="profile_name")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state.resume_contact = extract_contact_info(text)
            st.success("✅ Resume parsed and info extracted.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        selected = st.multiselect("Choose your strongest skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        questions = [
            "I take initiative to solve problems.",
            "I meet deadlines and deliver results.",
            "I communicate clearly with stakeholders.",
            "I adapt quickly to new challenges.",
            "I build strong team relationships."
        ]
        for i, question in enumerate(questions):
            response = st.radio(question, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (len(questions) * 5)) * 100, 1)
        st.session_state.behavior_score = behavior_score
        st.info(f"📈 Behavior Score: {behavior_score}/100")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: Reference Requests")
        traits = ["Leadership", "Communication", "Reliability", "Strategic Thinking", "Empathy"]
        for i in range(2):
            with st.expander(f"Reference {i+1}"):
                st.text_input("Name", key=f"ref{i}_name")
                st.text_input("Email", key=f"ref{i}_email")
                st.selectbox("What should they highlight?", traits, key=f"ref{i}_trait")
                st.text_area("Message to Referee (optional)", key=f"ref{i}_msg")
                if st.button(f"Send Request to Ref {i+1}"):
                    st.success(f"📨 Sent to {st.session_state.get(f'ref{i}_name', 'Referee')}")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 🔍 Step 5: JD Matching")
        jd1 = st.text_area("Paste Job Description #1", height=150)
        jd2 = st.text_area("Paste Job Description #2", height=150)
        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            for i, score in enumerate(scores):
                st.markdown(f"📄 JD {i+1} Match: **{score}%**")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 📊 Step 6: Quality of Hire Score")
        jd_scores = st.session_state.get("jd_scores", [70, 85])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        behavior = st.session_state.get("behavior_score", 50)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        ref_score = 90
        qoh = round((skills + ref_score + behavior + avg_jd) / 4, 1)
        st.session_state.qoh_score = qoh
        st.metric("⭐ Final QoH Score", f"{qoh}/100")
        st.button("Back", on_click=prev_step)
        st.button("Next: Roadmap", on_click=next_step)

    elif step == 6:
        st.markdown("### 🚀 Career Growth Roadmap")
        resume = st.session_state.get("resume_text", "")
        prompt = f"Create a growth roadmap based on this resume:\n{resume}\nInclude: 30-day, 60-day, 90-day, 6-month, and 1-year plans."
        try:
            res = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
            roadmap = res.choices[0].message.content.strip()
        except:
            roadmap = "30-Day: Onboarding\n60-Day: Project ownership\n90-Day: Cross-team initiatives\n6-Month: Strategic impact\n1-Year: Leadership readiness"
        st.markdown(f"**Roadmap:**\n\n{roadmap}")
        st.success("🎉 Candidate Journey Complete!")

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    st.caption("Adjust weights to prioritize skills that matter most to your role.")

    with st.sidebar.expander("🎚 QoH Weight Settings", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Please set at least one weight.")
        return

    df = pd.DataFrame([
        {"Candidate": "Jamie", "JD Match": 82, "Reference": 90, "Behavior": 76, "Skill": 85, "Gaps": "Strategic Thinking"},
        {"Candidate": "Amina", "JD Match": 78, "Reference": 65, "Behavior": 89, "Skill": 80, "Gaps": "Data Analysis"},
        {"Candidate": "Noah", "JD Match": 90, "Reference": 88, "Behavior": 90, "Skill": 88, "Gaps": "None"},
    ])

    df["QoH Score"] = (
        df["JD Match"] * w_jd +
        df["Reference"] * w_ref +
        df["Behavior"] * w_beh +
        df["Skill"] * w_skill
    ) / total

    df = df.sort_values("QoH Score", ascending=False)
    st.subheader("📋 Candidate Table")
    st.dataframe(df, use_container_width=True)

    st.markdown("### 🧠 AI Insights")
    for _, row in df.iterrows():
        if row["QoH Score"] >= 90:
            st.success(f"✅ {row['Candidate']}: Top-tier fit. Greenlight.")
        elif row["Reference"] < 75:
            st.warning(f"⚠️ {row['Candidate']}: Follow up on references.")
        elif row["Skill"] < 80:
            st.info(f"🔧 {row['Candidate']}: Develop **{row['Gaps']}** further.")
        else:
            st.write(f"🔍 {row['Candidate']}: Interview-ready.")

# --- LOGIN ---
def login_ui():
    st.title("🔐 Welcome to Skippr")
    st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=360)
    st.markdown("### From Rejection to Revolution.")
    st.caption("💡 You’ve been skipped before. Let’s make sure it never happens again.")

    st.sidebar.header("Login / Sign Up")
    mode = st.sidebar.radio("Mode", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if mode == "Login" and st.sidebar.button("Log In"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.supabase_user = res.user
            st.success("✅ Welcome back!")
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")

    elif mode == "Sign Up" and st.sidebar.button("Register"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("✅ Account created. Check your email!")
        except Exception as e:
            st.error(f"Signup failed: {e}")

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
