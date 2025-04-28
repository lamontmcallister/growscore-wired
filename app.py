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

# --- Candidate Journey ---
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
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        skills_pool = ["Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
                       "Communication", "Strategic Planning", "Excel", "Project Management"]
        selected = st.multiselect("Choose your strongest skills:", skills_pool)
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
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
        st.markdown("### 🎓 Step 5: Education")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Grad Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 📄 Step 6: Job Match")
        jd1 = st.text_area("Paste Job Description 1")
        jd2 = st.text_area("Paste Job Description 2")
        if jd1 and "resume_text" in st.session_state:
            jd_scores = [85, 90]  # Placeholder
            st.session_state.jd_scores = jd_scores
            for i, score in enumerate(jd_scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 📊 Step 7: Quality of Hire Score")
        jd_scores = st.session_state.get("jd_scores", [75, 80])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        ref = 90
        qoh = round((skills + behavior + ref + avg_jd) / 4, 1)
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 🚀 Step 8: Growth Roadmap")
        prompt = f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\nCreate a career roadmap:\n• 30-day\n• 60-day\n• 90-day\n• 6-month\n• 1-year"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Onboard\n• 60-Day: Deliver small win\n• 90-Day: Lead initiative\n• 6-Month: Strategic growth\n• 1-Year: Prepare for promotion"
        st.markdown(roadmap)
        st.session_state["growth_roadmap_text"] = roadmap
        st.success("🎉 Complete!")

        # --- FINAL STEP: SAVE PROFILE LOGIC ---
        st.markdown("### 📩 Save Your Profile")
        if st.button("Save My Profile"):
            selected_skills = st.session_state.get("selected_skills", [])
            jd_scores_list = st.session_state.get("jd_scores", [])
            user_email = st.session_state.supabase_user.user.email if st.session_state.get("supabase_user") else "anonymous"

            profile_data = {
                "user_email": user_email,
                "name": st.session_state.get("cand_name", ""),
                "job_title": st.session_state.get("cand_title", ""),
                "resume_text": st.session_state.get("resume_text", ""),
                "selected_skills": json.dumps(selected_skills),
                "behavior_score": st.session_state.get("behavior_score", 0),
                "reference_data": json.dumps({"mock": "data"}),
                "education": json.dumps({"mock": "data"}),
                "qoh_score": st.session_state.get("qoh_score", 0),
                "jd_scores": json.dumps(jd_scores_list),
                "growth_roadmap": roadmap,
                "timestamp": datetime.utcnow().isoformat()
            }

            try:
                result = supabase.table("profiles").insert(profile_data).execute()
                if result.status_code in [200, 201]:
                    st.success("✅ Profile saved successfully!")
                else:
                    st.error(f"❌ Failed to save profile. Status code: {result.status_code}")
            except Exception as e:
                st.error(f"❌ Error saving profile: {e}")

# --- Recruiter Dashboard ---
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

# --- MAIN ---
def main():
    login_section()
    if st.session_state.get("supabase_user"):
        menu = ["Candidate", "Recruiter Dashboard"]
        choice = st.sidebar.selectbox("Menu", menu)
        if choice == "Candidate":
            candidate_journey()
        else:
            recruiter_dashboard()
    else:
        st.warning("Please log in to access GrowScore features.")

if __name__ == "__main__":
    main()
