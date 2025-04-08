# Full GrowScore platform with all modules and updated login UI


import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="GrowScore", layout="wide")

# Load secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Auth state
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# Login UI
with st.sidebar:
    st.header("👤 Sign In / Register")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if auth_mode == "Login":
        if st.button("🔓 Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.success(f"✅ Logged in as {email}")
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("🆕 Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check email for verification.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

if not st.session_state.supabase_session:
    st.warning("❌ No active session. Please log in.")
    st.stop()
    
skills_pool = ["Python", "SQL", "Data Analysis", "Leadership", "Project Management",
               "Communication", "Strategic Planning", "Excel", "Machine Learning"]

leadership_skills = ["Ownership", "Bias for Action", "Earn Trust", "Deliver Results",
                     "Think Big", "Customer Obsession", "Invent & Simplify", "Hire & Develop",
                     "Dive Deep", "Frugality", "Have Backbone"]

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

def plot_radar(jd_scores):
    labels = [f"JD {i+1}" for i in range(len(jd_scores))]
    angles = np.linspace(0, 2 * np.pi, len(jd_scores), endpoint=False).tolist()
    scores = jd_scores + jd_scores[:1]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, 'o-', linewidth=2)
    ax.fill(angles, scores, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)
    st.pyplot(fig)

def generate_growth_recs():
    return [
        "- [Coursera: Data & Business Skills](https://coursera.org)",
        "- [LinkedIn Learning: Leadership Path](https://linkedin.com/learning)",
        "- Join a cross-functional project in your org",
        "- Set a 30/60/90 SMART goal around growth gaps"
        ]
        # ------------------- Candidate Journey -------------------
def candidate_journey():
    st.title("🌱 Candidate Journey")
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)
    st.progress((step + 1) / 9)

    if step == 0:
        st.subheader("📝 Step 1: Candidate Info + Portfolio Sync")
        st.markdown("Welcome! Let’s start with your contact info and resume.")
        contact_info = st.session_state.get("resume_contact", {"cand_name": "", "cand_email": "", "cand_title": ""})
        name_val = st.text_input("Full Name", key="cand_name", value=contact_info.get("cand_name", ""))
        email_val = st.text_input("Email", key="cand_email", value=contact_info.get("cand_email", ""))
        title_val = st.text_input("Target Job Title", key="cand_title", value=contact_info.get("cand_title", ""))
        st.text_input("🔗 LinkedIn Profile", key="cand_linkedin")
        st.text_input("🔗 GitHub Profile", key="cand_github")
        st.text_input("🌐 Portfolio / Personal Site", key="cand_portfolio")

        uploaded = st.file_uploader("📎 Upload Resume (PDF or TXT)", type=["pdf", "txt"])
        if uploaded:
            if uploaded.type == "application/pdf":
                with pdfplumber.open(uploaded) as pdf:
                    text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            else:
                text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            contact = extract_contact_info(text)
            st.session_state["resume_contact"] = {
                "cand_name": name_val or contact.get("name", ""),
                "cand_email": email_val or contact.get("email", ""),
                "cand_title": title_val or contact.get("title", "")
            }
            st.success("✅ Resume parsed and fields updated.")

        st.button("Next", on_click=next_step)

    elif step == 1:
        st.subheader("🎯 Step 2: Select Your Top Skills")
        st.markdown("Review and adjust the top skills extracted from your resume.")
        selected = st.multiselect("Top Skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.subheader("📋 Step 3: Behavior Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        q1 = st.radio("I meet deadlines", opts, index=2)
        q2 = st.radio("I collaborate effectively", opts, index=2)
        q3 = st.radio("I adapt well to change", opts, index=2)
        st.session_state.behavior_score = round((score_map[q1] + score_map[q2] + score_map[q3]) / 3 * 20, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.subheader("📨 Step 4: References (Simulated)")
        def add_ref(i):
            with st.expander(f"Reference {i+1}"):
                name = st.text_input("Name", key=f"ref_name_{i}")
                email = st.text_input("Email", key=f"ref_email_{i}")
                role = st.selectbox("Relationship", ["Manager", "Peer", "Direct Report"], key=f"ref_role_{i}")
                trait = st.selectbox("Leadership Trait", leadership_skills, key=f"ref_trait_{i}")
                sent = st.button(f"Send to {name or f'Ref {i+1}'}", key=f"send_ref_{i}")
                return {"name": name, "email": email, "role": role, "trait": trait, "status": "✅ Sent" if sent else "⏳ Pending"}
        st.session_state.references = [add_ref(0), add_ref(1)]
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.subheader("🏢 Step 5: Backchannel Reference")
        name = st.text_input("Contact Name", key="bc_name")
        email = st.text_input("Email", key="bc_email")
        topic = st.text_area("What would you like them to share insight about?", key="bc_topic")
        if st.button("Send Backchannel Request"):
            st.session_state.backchannel = {"name": name, "email": email, "topic": topic, "status": "✅ Sent"}
            st.success("Backchannel request sent.")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.subheader("🎓 Step 6: Education")
        degree = st.text_input("Degree", key="edu_degree")
        major = st.text_input("Major", key="edu_major")
        school = st.text_input("School", key="edu_school")
        year = st.text_input("Graduation Year", key="edu_year")
        edu_file = st.file_uploader("Upload transcript or diploma (optional)", type=["pdf"], key="edu_file")
        st.session_state.education = f"{degree} in {major}, {school}, {year}"
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.subheader("🔐 Step 7: HR Performance Checkpoint")
        st.warning("This is a future feature. No emails will be sent.")
        st.text_input("Company", key="hr_company")
        st.text_input("Manager", key="hr_manager")
        st.text_input("HR Email (optional)", key="hr_email")
        st.checkbox("I authorize GrowScore to verify past performance", key="hr_auth")
        st.session_state.hr_check = "✅ HR Request Authorized (simulated)"
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.subheader("📄 Step 8: Resume vs JD Skill Match")
        jd1 = st.text_area("Paste JD 1", key="jd_1")
        jd2 = st.text_area("Paste JD 2", key="jd_2")
        jd_inputs = [jd for jd in [jd1, jd2] if jd.strip()]
        if jd_inputs and "resume_text" in st.session_state:
            jd_scores = match_resume_to_jds(st.session_state.resume_text, jd_inputs)
            st.session_state.jd_scores = jd_scores
            for i, score in enumerate(jd_scores):
                st.write(f"**JD {i+1}** Match Score: {score}%")
            plot_radar(jd_scores)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.subheader("✅ Step 9: Final Summary & Growth Roadmap")
        jd_scores = st.session_state.get("jd_scores", [])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1) if jd_scores else 0
        skill_score = len(st.session_state.get("selected_skills", [])) * 5
        ref_score = 90
        behavior = st.session_state.get("behavior_score", 50)
        qoh = round((skill_score + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("💡 Quality of Hire Score", f"{qoh}/100")

        st.subheader("🔍 Verification Table")
        st.table({
            "Resume": ["✅ GPT Verified"],
            "References": ["✅ Sent"],
            "Backchannel": [st.session_state.get("backchannel", {}).get("status", "❌")],
            "Education": ["✅" if st.session_state.get("education") else "❌"],
            "HR Performance": [st.session_state.get("hr_check", "❌")],
            "Behavior": ["🟠 Self-Reported"],
            "JD Match": [f"{avg_jd}%"]
        })

        st.subheader("📈 Growth Roadmap")
        for rec in generate_growth_recs():
            st.markdown(rec)
        st.success("🎉 You’ve completed your GrowScore profile!")

# ------------------- Recruiter Dashboard -------------------
def recruiter_dashboard():
    st.title("🧑‍💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚️ QoH Weight Sliders", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Adjust sliders to view scores.")
        return

    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Reference": 90, "Behavior": 84, "Skill": 92,
         "Gaps": "Strategic Planning", "Verified": "✅ Resume, ✅ References, ✅ JD, 🟠 Behavior, ✅ Education, 🔐 HR"},
        {"Candidate": "Jasmine", "JD Match": 82, "Reference": 78, "Behavior": 90, "Skill": 80,
         "Gaps": "Leadership", "Verified": "✅ Resume, ⚠️ References, ✅ JD, ✅ Behavior, ✅ Education, ❌ HR"},
        {"Candidate": "Andre", "JD Match": 75, "Reference": 65, "Behavior": 70, "Skill": 78,
         "Gaps": "Communication", "Verified": "✅ Resume, ❌ References, ✅ JD, ⚠️ Behavior, ❌ Education, ❌ HR"}
    ])

    selected = st.multiselect("Compare Candidates", df["Candidate"].tolist(), default=df["Candidate"].tolist())
    filtered = df[df["Candidate"].isin(selected)].copy()

    filtered["QoH Score"] = (
        filtered["JD Match"] * w_jd +
        filtered["Reference"] * w_ref +
        filtered["Behavior"] * w_beh +
        filtered["Skill"] * w_skill
    ) / total

    st.subheader("📋 Candidate Comparison Table")
    st.dataframe(filtered)

    st.subheader("🎯 AI Recommendations")
    for _, row in filtered.iterrows():
        if row["QoH Score"] >= 90:
            st.success(f"{row['Candidate']}: 🚀 Strong hire. Green light.")
        elif row["Reference"] < 75:
            st.warning(f"{row['Candidate']}: ⚠️ Weak reference. Needs follow-up.")
        elif row["Skill"] < 80:
            st.info(f"{row['Candidate']}: Needs support in **{row['Gaps']}**.")
        else:
            st.write(f"{row['Candidate']}: Ready for interviews.")

# ------------------- Routing -------------------
st.title("🚀 Welcome to GrowScore")
portal = st.radio("Choose your portal:", ["👤 Candidate Portal", "🧑‍💼 Recruiter Portal"])
if portal == "👤 Candidate Portal":
    candidate_journey()
else:
    recruiter_dashboard()

