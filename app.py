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

load_custom_css()

# --- SESSION STATE ---
for k in ["supabase_session", "supabase_user", "step"]:
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
            st.session_state["resume_contact"] = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        selected = st.multiselect("Choose your strongest skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.caption("Tell us how you show up at work. Choose the statement that best reflects you for each trait.")
        behavior_questions = {
            "Meets deadlines consistently": None,
            "Collaborates well in teams": None,
            "Adapts quickly to change": None,
            "Demonstrates leadership": None,
            "Communicates effectively": None,
        }
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        for i, question in enumerate(behavior_questions):
            response = st.radio(question, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (len(behavior_questions) * 5)) * 100, 1)
        st.session_state.behavior_score = behavior_score
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        st.text_input("Reference Name")
        st.text_input("Reference Email")
        st.selectbox("Trait Highlighted by Reference", skills_pool)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Backchannel Check (Optional)")
        st.text_input("Backchannel Contact Name")
        st.text_input("Backchannel Email")
        st.text_area("Message or Topic for Feedback")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education Background")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Graduation Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 🏢 Step 7: HR Verification")
        st.text_input("Most Recent Company")
        st.text_input("Manager's Name")
        st.text_input("HR Contact Email")
        st.checkbox("I authorize verification with these contacts")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: JD Matching & Skills Gap")
        jd1 = st.text_area("Paste Job Description 1", height=150)
        jd2 = st.text_area("Paste Job Description 2", height=150)

        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            st.success("✅ JD Matching Complete")

            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire Summary")
        jd_scores = st.session_state.get("jd_scores", [70, 80])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        ref_score = 90
        behavior = st.session_state.get("behavior_score", 50)
        qoh = round((skills + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("📈 Quality of Hire (QoH)", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Career Growth Roadmap")
        prompt = f"Based on this resume:\n{st.session_state.get('resume_text', '')}\n\nCreate a career roadmap with:\n- 30-day\n- 60-day\n- 90-day\n- 6-month\n- 1-year plan."
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Get started\n• 60-Day: Deliver a win\n• 90-Day: Lead an initiative\n• 6-Month: Strategic growth\n• 1-Year: Promotion ready"
        st.markdown(f"**Your Roadmap:**\n\n{roadmap}")
        st.success("🎉 Candidate Journey Complete!")

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        candidate_journey()
    else:
        st.write("Recruiter Dashboard Placeholder")
else:
    st.title("🔐 Please log in to start your journey.")
