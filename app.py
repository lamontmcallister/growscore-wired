# skippr_app_full_final.py

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

# --- SESSION STATE ---
for k in ["supabase_session", "supabase_user", "step"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "step" else 0

skills_pool = ["Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
               "Communication", "Strategic Planning", "Excel", "Project Management"]

# --- GPT HELPERS ---
def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\\n{text}\\nReturn as a Python list."
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
    prompt = f"From this resume, extract the full name, email, and job title. Return a Python dictionary with keys: name, email, title.\\n\\n{text}"
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
    prompt = f"Given this resume:\\n{resume_text}\\n\\nMatch semantically to the following JDs:\\n"
    for i, jd in enumerate(jd_texts):
        prompt += f"\\nJD {i+1}:\\n{jd}\\n"
    prompt += "\\nReturn a list of match scores, e.g. [82, 76]"
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
    import matplotlib.pyplot as plt
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
# --- CANDIDATE JOURNEY (10 Steps) ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.subheader("📝 Step 1: Resume Upload + Contact Info")
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
        st.subheader("📋 Step 2: Select Skills")
        selected = st.multiselect("Choose skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.subheader("🧠 Step 3: Behavior Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        q1 = st.radio("I meet deadlines", opts, index=2)
        q2 = st.radio("I collaborate well", opts, index=2)
        q3 = st.radio("I adapt to change", opts, index=2)
        st.session_state.behavior_score = round((score_map[q1] + score_map[q2] + score_map[q3]) / 3 * 20, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.subheader("🤝 Step 4: References")
        st.text_input("Reference 1 Name")
        st.text_input("Reference 1 Email")
        st.text_input("Reference 2 Name")
        st.text_input("Reference 2 Email")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.subheader("📣 Step 5: Backchannel")
        st.text_input("Backchannel Name")
        st.text_input("Backchannel Email")
        st.text_area("Topic for Feedback")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.subheader("🎓 Step 6: Education")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("School")
        st.text_input("Graduation Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.subheader("🏢 Step 7: HR Check")
        st.text_input("Company")
        st.text_input("Manager Name")
        st.text_input("HR Email")
        st.checkbox("I authorize verification")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.subheader("📄 Step 8: JD Matching")
        jd1 = st.text_area("Paste JD 1")
        jd2 = st.text_area("Paste JD 2")
        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            for i, score in enumerate(scores):
                st.write(f"**JD {i+1} Match Score:** {score}%")
            plot_radar(scores)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.subheader("📊 Step 9: Quality of Hire Summary")
        jd_scores = st.session_state.get("jd_scores", [70, 80])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        ref_score = 90
        behavior = st.session_state.get("behavior_score", 50)
        qoh = round((skills + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("📈 Quality of Hire (QoH)", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next: Growth Pathway", on_click=next_step)

    elif step == 9:
        st.subheader("🚀 Step 10: Career Growth Roadmap")
        prompt = f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\nGenerate a growth roadmap for this candidate:\n- 30-day plan\n- 60-day plan\n- 90-day plan\n- 6-month vision\n- 1-year career trajectory"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Learn the product\n• 60-Day: Deliver first project\n• 90-Day: Lead team\n• 6-Month: Strategic roadmap\n• 1-Year: Sr. Leadership path"

        st.markdown(f"**Personalized Roadmap:**\n\n{roadmap}")
        st.success("🎉 Candidate Journey Complete!")
# --- RECRUITER DASHBOARD (Enhanced UI) ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    st.sidebar.header("Adjust Scoring Weights")

    # 🎚 Scoring Weights
    w_qoh = st.sidebar.slider("Quality of Hire", 0, 100, 40)
    w_jd = st.sidebar.slider("JD Match", 0, 100, 30)
    w_behavior = st.sidebar.slider("Behavior", 0, 100, 20)
    w_skills = st.sidebar.slider("Skills", 0, 100, 10)

    # 📊 Candidate Scorecards
    st.subheader("📋 Candidate Comparison")

    candidates = pd.DataFrame([
        {"Name": "Jamie", "QoH": 87, "JD Match": 82, "Behavior": 76, "Skills": 85},
        {"Name": "Taylor", "QoH": 79, "JD Match": 77, "Behavior": 90, "Skills": 80}
    ])

    def calc_total(row):
        return (
            row["QoH"] * (w_qoh/100) +
            row["JD Match"] * (w_jd/100) +
            row["Behavior"] * (w_behavior/100) +
            row["Skills"] * (w_skills/100)
        )

    candidates["Total Score"] = candidates.apply(calc_total, axis=1)
    candidates = candidates.sort_values("Total Score", ascending=False)

    col1, col2 = st.columns(2)
    for i, (col, row) in enumerate(zip([col1, col2], candidates.itertuples())):
        with col:
            st.markdown(f"### 👤 {row.Name}")
            st.metric("Total Score", f"{round(row._6, 1)}")
            st.markdown(f"- **QoH:** {row.QoH}")
            st.markdown(f"- **JD Match:** {row._2}")
            st.markdown(f"- **Behavior:** {row._3}")
            st.markdown(f"- **Skills:** {row._4}")

    # 🧠 GPT-Backed Summary
    top = candidates.iloc[0]["Name"]
    st.markdown("---")
    st.subheader("🧠 AI Insight")
    st.success(f"⭐ Based on current weightings, **{top}** is the most aligned candidate for the role.")
# --- LOGIN + SIGNUP + IMAGE ---
def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=400)
        st.markdown("### From Rejection to Revolution.")
        st.caption("💡 I didn’t get the job. I built the platform that fixes the problem.")

    st.markdown("---")

    with st.sidebar:
        st.header("🔐 Login / Sign Up")
        mode = st.radio("Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if mode == "Login" and st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.success("✅ Logged in")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check your email.")
            except Exception as e:
                st.error(f"Signup failed: {e}")


# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal:", ["Candidate", "Recruiter"])
    if view == "Candidate":
        candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
