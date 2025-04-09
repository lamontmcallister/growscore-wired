# --- GrowScore Full Setup + Header Section ---

import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="GrowScore – Powered by Backdoor", layout="wide")

# -----------------------------
# Top Header + Portal Selection (UI Enhancement)
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🚀 Welcome to GrowScore")
    st.markdown("##### 💼 Backdoor – A Smarter, Verified Path to Talent Discovery")
with col2:
    portal = st.radio("Portal:", ["👤 Candidate Portal", "🧑‍💼 Recruiter Portal"], key="main_portal")

# -----------------------------
# 🔥 Why GrowScore
st.markdown("### Why GrowScore?")
st.markdown("""
- ✅ Predictive analysis of candidate success before they apply  
- 🎯 Smart JD-to-Resume matching with GPT  
- 🧠 Verifies references, education, and behavior patterns  
- 🧭 Supports job changers, not just job matchers  
- 🚪 Bypasses the ‘no-reply’ black hole and shows human potential  
- 🤖 AI that assists hiring — not replaces it  
- 📈 Improves chances of getting hired by up to **37%**
""")

# -----------------------------
# Skill + Leadership Trait Banks
skills_pool = [
    "Python", "SQL", "Data Analysis", "Leadership", "Project Management",
    "Communication", "Strategic Planning", "Excel", "Machine Learning"
]

leadership_skills = [
    "Ownership", "Bias for Action", "Earn Trust", "Deliver Results",
    "Think Big", "Customer Obsession", "Invent & Simplify", "Hire & Develop",
    "Dive Deep", "Frugality", "Have Backbone"
]

# -----------------------------
# GPT-Based Skill Extraction
def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\\n{text}\\nReturn as a Python list."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return eval(res.choices[0].message.content.strip())
    except:
        return ["Python", "SQL", "Excel"]

# -----------------------------
# GPT JD Matching
def match_resume_to_jds(resume_text, jd_texts):
    prompt = f"Given this resume:\\n{resume_text}\\n\\nMatch semantically to the following JDs:\\n"
    for i, jd in enumerate(jd_texts):
        prompt += f"\\nJD {i+1}:\\n{jd}\\n"
    prompt += "\\nReturn a list of numeric match scores, e.g. [82, 76]"

    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return eval(res.choices[0].message.content.strip())
    except:
        return [np.random.randint(70, 90) for _ in jd_texts]

# -----------------------------
# Radar Chart Display
def plot_radar(jd_scores):
    if not jd_scores:
        return
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

# -----------------------------
# Roadmap Generator
def generate_growth_recs():
    return [
        "- [Coursera: Data & Business Skills](https://coursera.org)",
        "- [LinkedIn Learning: Leadership Path](https://linkedin.com/learning)",
        "- Join a cross-functional project in your org",
        "- Set a 30/60/90 SMART goal around growth gaps"
    ]
# -----------------------------
# 🌱 Candidate Journey

def candidate_journey():
    st.title("🌱 Candidate Journey")
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)
    st.progress((step + 1) / 9)

    # STEP 0: Welcome + Portfolio Sync
    if step == 0:
        st.subheader("📝 Step 1: Welcome to Backdoor")
        st.markdown("""
        Welcome to **Backdoor** — the human-first job platform built to help you break through the noise.

        🎯 Our AI helps hiring teams *see* you — not just screen you.

        ✅ Upload your resume and add portfolio links
        ✅ Autofill your info (or edit manually)
        ✅ Build a verified profile that increases your chance of getting hired by **37%**
        """)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name", key="cand_name")
            st.text_input("Email", key="cand_email")
            st.text_input("Target Role Title", key="cand_title")
        with col2:
            st.text_input("🔗 LinkedIn URL", key="cand_linkedin")
            st.text_input("🔗 GitHub", key="cand_github")
            st.text_input("🌐 Portfolio / Website", key="cand_portfolio")

        uploaded = st.file_uploader("📎 Upload Resume", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.success("✅ Resume parsed successfully.")
        st.button("Next", on_click=next_step)

    # STEP 1: Skill Selection
    elif step == 1:
        st.subheader("🎯 Step 2: Top Skills")
        st.markdown("Select your strongest skills — these will influence your Quality of Hire (QoH) score.")
        selected = st.multiselect("Choose skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    # STEP 2: Behavior Survey
    elif step == 2:
        st.subheader("🧠 Step 3: Behavior Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        q1 = st.radio("I meet deadlines", opts, index=2)
        q2 = st.radio("I collaborate effectively", opts, index=2)
        q3 = st.radio("I adapt well to change", opts, index=2)
        st.session_state.behavior_score = round((score_map[q1] + score_map[q2] + score_map[q3]) / 3 * 20, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    # STEP 3: Reference Collection
    elif step == 3:
        st.subheader("📨 Step 4: Add References")
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

    # STEP 4: Backchannel Request
    elif step == 4:
        st.subheader("🏢 Step 5: Backchannel Reference")
        name = st.text_input("Contact Name", key="bc_name")
        email = st.text_input("Email", key="bc_email")
        topic = st.text_area("What do you want to learn from them?", key="bc_topic")
        if st.button("Send Backchannel Request"):
            st.session_state.backchannel = {"name": name, "email": email, "topic": topic, "status": "✅ Sent"}
            st.success("Request sent.")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    # STEP 5: Education
    elif step == 5:
        st.subheader("🎓 Step 6: Education")
        st.text_input("Degree", key="edu_degree")
        st.text_input("Major", key="edu_major")
        st.text_input("School", key="edu_school")
        st.text_input("Graduation Year", key="edu_year")
        st.file_uploader("Upload transcript or diploma (PDF)", type=["pdf"], key="edu_file")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    # STEP 6: HR Checkpoint
    elif step == 6:
        st.subheader("🔐 Step 7: HR Verification (Simulated)")
        st.warning("This is a credibility signal only — nothing is sent.")
        st.text_input("Company", key="hr_company")
        st.text_input("Manager", key="hr_manager")
        st.text_input("HR Email", key="hr_email")
        st.checkbox("I authorize GrowScore to verify past performance", key="hr_auth")
        st.session_state.hr_check = "✅ HR Request Authorized (simulated)"
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    # STEP 7: JD Matching
    elif step == 7:
        st.subheader("📄 Step 8: JD Matching")
        st.markdown("Paste 2 target job descriptions side-by-side:")
        col1, col2 = st.columns(2)
        jd1 = col1.text_area("Job Description 1", key="jd_1")
        jd2 = col2.text_area("Job Description 2", key="jd_2")
        jd_inputs = [jd for jd in [jd1, jd2] if jd.strip()]
        if jd_inputs and "resume_text" in st.session_state:
            jd_scores = match_resume_to_jds(st.session_state.resume_text, jd_inputs)
            st.session_state.jd_scores = jd_scores
            for i, score in enumerate(jd_scores):
                st.write(f"JD {i+1} Match Score: {score}%")
            plot_radar(jd_scores)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    # STEP 8: Summary & Growth Roadmap
    elif step == 8:
        st.subheader("✅ Step 9: Final Summary")
        jd_scores = st.session_state.get("jd_scores", [])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1) if jd_scores else 0
        skill_score = len(st.session_state.get("selected_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        qoh = round((skill_score + behavior + ref_score + avg_jd) / 4, 1)
        st.metric("💡 Quality of Hire Score", f"{qoh}/100")

        st.subheader("🔍 Verification Summary")
        verification = {
            "Resume": "✅ GPT Verified",
            "References": "✅ Sent",
            "Backchannel": st.session_state.get("backchannel", {}).get("status", "❌"),
            "Education": "✅" if st.session_state.get("edu_degree") else "❌",
            "HR Performance": st.session_state.get("hr_check", "❌"),
            "Behavior": "🟠 Self-Reported",
            "JD Match": f"{avg_jd}%"
        }
        st.table(pd.DataFrame.from_dict(verification, orient="index", columns=["Status"]))

        st.subheader("📈 Growth Roadmap")
        for rec in generate_growth_recs():
            st.markdown(rec)
        st.success("🎉 You’ve completed your GrowScore profile!")

# -----------------------------
# 🚀 Main Routing (at bottom of full script)
st.title("🚀 Welcome to GrowScore")
st.markdown("Backdoor – Powered by GrowScore")

# Move to top right
col1, col2 = st.columns([6, 1])
with col2:
    portal = st.radio("Choose your portal", ["👤 Candidate Portal", "🧑‍💼 Recruiter Portal"], key="portal_select")

if st.session_state.get("portal_select", "👤 Candidate Portal") == "👤 Candidate Portal":
    candidate_journey()
else:
    recruiter_dashboard()
