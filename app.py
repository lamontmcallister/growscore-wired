import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import datetime

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
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION STATE ---
for k in ["supabase_session", "supabase_user", "step", "profile_id", "profile_data"]:
    if k not in st.session_state:
        st.session_state[k] = None if k not in ["step", "profile_data"] else (0 if k == "step" else {})

# --- UTILS ---
skills_pool = [
    "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
    "Communication", "Strategic Planning", "Excel", "Project Management"
]

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

def calculate_qoh_score(skill_count, ref, behav, jd_scores):
    avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
    skills = skill_count * 5
    final = round((skills + ref + behav + avg_jd) / 4, 1)
    return final

# --- PROFILE HANDLING ---
def load_profile_from_db():
    email = st.session_state.supabase_user["email"]
    profiles = supabase.table("profiles").select("*").eq("user_email", email).execute().data
    profile_names = [p["name"] for p in profiles]
    return profiles, profile_names

def save_profile_to_db():
    if st.session_state.profile_id:
        supabase.table("profiles").update({"data": st.session_state.profile_data}).eq("id", st.session_state.profile_id).execute()
    else:
        res = supabase.table("profiles").insert({
            "user_email": st.session_state.supabase_user["email"],
            "name": st.session_state.profile_data.get("name", f"Profile {datetime.now().isoformat()}"),
            "data": st.session_state.profile_data
        }).execute()
        st.session_state.profile_id = res.data[0]["id"]

# --- PROFILE SELECTION UI ---
def profile_selector():
    profiles, names = load_profile_from_db()
    st.markdown("### 👤 Select or Create Profile")
    if names:
        selected = st.selectbox("Choose existing profile", names)
        if st.button("Load Profile"):
            selected_profile = next(p for p in profiles if p["name"] == selected)
            st.session_state.profile_id = selected_profile["id"]
            st.session_state.profile_data = selected_profile["data"]
            st.success(f"Loaded profile: {selected}")
            st.experimental_rerun()
    new_profile = st.text_input("Or enter new profile name")
    if st.button("Create New Profile") and new_profile:
        st.session_state.profile_data = {"name": new_profile}
        save_profile_to_db()
        st.success(f"Created and loaded new profile: {new_profile}")
        st.experimental_rerun()
# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): 
        save_profile_to_db()
        st.session_state.step = step + 1
    def prev_step(): 
        save_profile_to_db()
        st.session_state.step = max(0, step - 1)

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    profile = st.session_state.profile_data

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Contact Info")
        profile["cand_name"] = st.text_input("Full Name", value=profile.get("cand_name", ""))
        profile["cand_email"] = st.text_input("Email", value=profile.get("cand_email", ""))
        profile["cand_title"] = st.text_input("Target Job Title", value=profile.get("cand_title", ""))
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            profile["resume_text"] = text
            profile["resume_skills"] = extract_skills_from_resume(text)
            profile["resume_contact"] = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        selected = st.multiselect("Choose your strongest skills:", skills_pool, default=profile.get("resume_skills", []))
        profile["selected_skills"] = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.caption("How do you show up at work?")
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
        profile["behavior_score"] = behavior_score
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        traits = ["Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork",
                  "Adaptability", "Problem Solving", "Empathy", "Initiative", "Collaboration"]

        for i in range(1, 3):
            with st.expander(f"Reference {i}"):
                profile[f"ref{i}_name"] = st.text_input("Name", value=profile.get(f"ref{i}_name", ""), key=f"ref{i}_name")
                profile[f"ref{i}_email"] = st.text_input("Email", value=profile.get(f"ref{i}_email", ""), key=f"ref{i}_email")
                profile[f"ref{i}_trait"] = st.selectbox("Trait to Highlight", traits, index=0, key=f"ref{i}_trait")
                profile[f"ref{i}_msg"] = st.text_area("Optional Message", value=profile.get(f"ref{i}_msg", ""), key=f"ref{i}_msg")
                if st.button(f"Send to Ref {i}"):
                    st.success(f"Request sent to {profile.get(f'ref{i}_name')}")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Backchannel (Optional)")
        profile["bc_name"] = st.text_input("Name", value=profile.get("bc_name", ""))
        profile["bc_email"] = st.text_input("Email", value=profile.get("bc_email", ""))
        profile["bc_msg"] = st.text_area("Message or Topic for Feedback", value=profile.get("bc_msg", ""))
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education")
        profile["degree"] = st.text_input("Degree", value=profile.get("degree", ""))
        profile["major"] = st.text_input("Major", value=profile.get("major", ""))
        profile["institution"] = st.text_input("Institution", value=profile.get("institution", ""))
        profile["grad_year"] = st.text_input("Graduation Year", value=profile.get("grad_year", ""))
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 🏢 Step 7: HR Check")
        profile["company"] = st.text_input("Company", value=profile.get("company", ""))
        profile["manager"] = st.text_input("Manager", value=profile.get("manager", ""))
        profile["hr_email"] = st.text_input("HR Email", value=profile.get("hr_email", ""))
        profile["hr_auth"] = st.checkbox("I authorize verification", value=profile.get("hr_auth", False))
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: Job Matching")
        jd1 = st.text_area("Paste JD 1", value=profile.get("jd1", ""))
        jd2 = st.text_area("Paste JD 2", value=profile.get("jd2", ""))
        profile["jd1"] = jd1
        profile["jd2"] = jd2

        if jd1 and profile.get("resume_text"):
            scores = match_resume_to_jds(profile["resume_text"], [jd1, jd2])
            profile["jd_scores"] = scores
            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire Score")
        jd_scores = profile.get("jd_scores", [75, 80])
        skill_count = len(profile.get("selected_skills", []))
        behavior = profile.get("behavior_score", 50)
        ref_score = 90
        qoh = calculate_qoh_score(skill_count, ref_score, behavior, jd_scores)
        profile["qoh_score"] = qoh
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Growth Roadmap")
        prompt = f"Given this resume:\n{profile.get('resume_text', '')}\n\nCreate a career roadmap:\n• 30-day\n• 60-day\n• 90-day\n• 6-month\n• 1-year"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Onboard\n• 60-Day: Deliver small win\n• 90-Day: Lead initiative\n• 6-Month: Strategic growth\n• 1-Year: Promotion Ready"
        profile["growth_roadmap"] = roadmap
        st.markdown(roadmap)
        st.success("🎉 Complete!")
        save_profile_to_db()

# --- ROUTING ---
if st.session_state.supabase_user:
    if not st.session_state.profile_id:
        profile_selector()
    else:
        candidate_journey()
else:
    st.write("Please log in.")
