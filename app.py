# --- This is the FULL corrected App.py file including all journey steps ---

import streamlit as st
import openai
import pdfplumber
import pandas as pd
import ast
import numpy as np
import json
from datetime import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

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
            growth_roadmap_text = response.choices[0].message.content.strip()
            st.markdown(growth_roadmap_text)
        except:
            growth_roadmap_text = "• 30-Day: Get oriented\n• 60-Day: Deliver project\n• 90-Day: Lead initiative\n• 6-Month: Exceed KPIs\n• 1-Year: Level up"
            st.markdown(growth_roadmap_text)
        st.success("🎉 Complete!")
        st.button("Back", on_click=prev_step)

        if st.button("Save Profile"):
            selected_skills = st.session_state.get("selected_skills", [])
            jd_scores_list = st.session_state.get("jd_scores", [])
            avg_jd_score = round(sum(jd_scores_list) / len(jd_scores_list), 2) if jd_scores_list else 0

            profile_data = {
                "name": st.session_state.get("cand_name", ""),
                "job_title": st.session_state.get("cand_title", ""),
                "resume_text": st.session_state.get("resume_text", ""),
                "selected_skills": json.dumps(selected_skills),
                "behavior_score": st.session_state.get("behavior_score", 0),
                "reference_data": json.dumps({"mock": "data"}),
                "education": json.dumps({"mock": "data"}),
                "qoh_score": st.session_state.get("qoh_score", 0),
                "jd_scores": avg_jd_score,
                "growth_roadmap": growth_roadmap_text,
            }

            try:
                result = supabase.table("profiles").insert(profile_data).execute()
                if result.status_code in [200, 201]:
                    st.success("✅ Profile saved successfully!")
                else:
                    st.error(f"❌ Failed to save profile. Status code: {result.status_code}")
            except Exception as e:
                st.error(f"❌ Error saving profile: {e}")

# --- MAIN ---
def main():
    candidate_journey()

if __name__ == "__main__":
    main()
