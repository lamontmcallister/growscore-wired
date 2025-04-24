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

# --- CSS ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] {
                font-family: 'Segoe UI', sans-serif;
            }
            h1, h2, h3 {
                font-weight: 600 !important;
            }
            div.stButton > button {
                background-color: #ff6a00;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0.5rem 1.2rem;
                font-weight: 600;
            }
            section[data-testid="stSidebar"] {
                background-color: #f9f4ef;
                border-right: 1px solid #e1dfdb;
            }
        </style>
    """, unsafe_allow_html=True)
load_custom_css()

# --- STATE INIT ---
for key in ["supabase_user", "supabase_session", "step", "active_profile", "profile_data"]:
    if key not in st.session_state:
        st.session_state[key] = 0 if key == "step" else None

# --- SKILLS ---
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

# --- PROFILE LOGIC ---
def fetch_profiles():
    user_id = st.session_state.supabase_user["id"]
    res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    profiles = res.data if res.data else []
    return profiles

def save_profile_data():
    user_id = st.session_state.supabase_user["id"]
    profile_name = st.session_state.active_profile
    current_data = st.session_state.profile_data

    match = supabase.table("profiles").select("*").eq("user_id", user_id).eq("name", profile_name).execute()
    if match.data:
        # Update existing
        supabase.table("profiles").update({
            "data": current_data
        }).eq("user_id", user_id).eq("name", profile_name).execute()
    else:
        # Insert new
        supabase.table("profiles").insert({
            "user_id": user_id,
            "name": profile_name,
            "data": current_data
        }).execute()
    st.success("💾 Profile saved!")

def load_profile_data(profile_id):
    match = supabase.table("profiles").select("*").eq("id", profile_id).execute()
    if match.data:
        st.session_state.profile_data = match.data[0]["data"]
        st.session_state.step = st.session_state.profile_data.get("step", 0)
        st.success("✅ Profile loaded successfully!")

def profile_selector():
    st.markdown("### 👤 Select or Create Profile")
    profiles = fetch_profiles()
    names = [p["name"] for p in profiles]
    selected = st.selectbox("Choose Existing", names)
    if st.button("Load Profile"):
        selected_id = [p["id"] for p in profiles if p["name"] == selected][0]
        st.session_state.active_profile = selected
        load_profile_data(selected_id)

    new_name = st.text_input("Or enter new profile name")
    if new_name and st.button("Create New"):
        st.session_state.active_profile = new_name
        st.session_state.profile_data = {}
        st.success(f"Created new profile: {new_name}")
# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): 
        st.session_state.step = step + 1
        st.session_state.profile_data["step"] = st.session_state.step
        save_profile_data()
    def prev_step(): 
        st.session_state.step = max(0, step - 1)
        st.session_state.profile_data["step"] = st.session_state.step
        save_profile_data()

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Contact Info")
        name = st.text_input("Full Name", key="cand_name")
        email = st.text_input("Email", key="cand_email")
        title = st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.profile_data["resume_text"] = text
            st.session_state.profile_data["resume_skills"] = extract_skills_from_resume(text)
            st.session_state.profile_data["resume_contact"] = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        selected = st.multiselect("Choose your strongest skills:", skills_pool, 
                                  default=st.session_state.profile_data.get("resume_skills", []))
        st.session_state.profile_data["selected_skills"] = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        for i, question in enumerate([
            "Meets deadlines consistently", "Collaborates well in teams", "Adapts quickly to change",
            "Demonstrates leadership", "Communicates effectively"
        ]):
            response = st.radio(question, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (5 * 5)) * 100, 1)
        st.session_state.profile_data["behavior_score"] = behavior_score
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        traits = ["Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork"]
        ref_data = {}
        for i in range(1, 3):
            with st.expander(f"Reference {i}"):
                ref_data[f"ref{i}_name"] = st.text_input("Name", key=f"ref{i}_name")
                ref_data[f"ref{i}_email"] = st.text_input("Email", key=f"ref{i}_email")
                ref_data[f"ref{i}_trait"] = st.selectbox("Trait to Highlight", traits, key=f"ref{i}_trait")
        st.session_state.profile_data["reference_data"] = ref_data
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Backchannel (Optional)")
        st.text_input("Name")
        st.text_input("Email")
        st.text_area("Message or Topic for Feedback")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education")
        edu = {
            "degree": st.text_input("Degree"),
            "major": st.text_input("Major"),
            "institution": st.text_input("Institution"),
            "grad_year": st.text_input("Graduation Year")
        }
        st.session_state.profile_data["education"] = edu
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 🏢 Step 7: HR Check")
        st.text_input("Company")
        st.text_input("Manager")
        st.text_input("HR Email")
        st.checkbox("I authorize verification")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: Job Matching")
        jd1 = st.text_area("Paste JD 1")
        jd2 = st.text_area("Paste JD 2")
        if jd1 and "resume_text" in st.session_state.profile_data:
            scores = match_resume_to_jds(st.session_state.profile_data["resume_text"], [jd1, jd2])
            st.session_state.profile_data["jd_scores"] = scores
            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire Score")
        jd_scores = st.session_state.profile_data.get("jd_scores", [75, 80])
        skill_count = len(st.session_state.profile_data.get("selected_skills", []))
        behavior = st.session_state.profile_data.get("behavior_score", 50)
        ref_score = 90
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = skill_count * 5
        qoh = round((skills + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.session_state.profile_data["qoh_score"] = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Growth Roadmap")
        prompt = f"Given this resume:\n{st.session_state.profile_data.get('resume_text', '')}\n\nCreate a career roadmap:\n• 30-day\n• 60-day\n• 90-day\n• 6-month\n• 1-year"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Onboard\n• 60-Day: Deliver small win\n• 90-Day: Lead initiative\n• 6-Month: Strategic growth\n• 1-Year: Promotion ready"
        st.markdown(roadmap)
        st.session_state.profile_data["growth_roadmap"] = roadmap
        st.success("🎉 Complete! Profile Saved Permanently.")
        save_profile_data()

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        if not st.session_state.active_profile:
            profile_selector()
        else:
            candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
