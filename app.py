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

# --- CUSTOM STYLING ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; padding: 0rem !important; }
            h1, h2, h3 { font-weight: 600 !important; margin-bottom: 0.5rem; }
            div.stButton > button { background-color: #ff6a00; color: white; border: none; border-radius: 6px; padding: 0.5rem 1.2rem; font-weight: 600; font-size: 1rem; margin-top: 0.5rem; }
            .stSlider > div { padding-top: 0.5rem; }
            section[data-testid="stSidebar"] { background-color: #f9f4ef; border-right: 1px solid #e1dfdb; }
            .markdown-block { background-color: #f8f8f8; padding: 1rem 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 1rem; }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION STATE ---
for k in ["supabase_session", "supabase_user", "step", "profiles", "active_profile", "profile_selected"]:
    if k not in st.session_state:
        if k == "step":
            st.session_state[k] = 0
        elif k == "profiles":
            st.session_state[k] = {}
        elif k == "profile_selected":
            st.session_state[k] = False
        else:
            st.session_state[k] = None

# --- HELPER FUNCTIONS ---
def ensure_profile_initialized(profile_name):
    if profile_name not in st.session_state.profiles:
        st.session_state.profiles[profile_name] = {"progress": {}}

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
    return final, {"Skills": skills, "References": ref, "Behavior": behav, "JD Match": avg_jd}

# --- PROFILE MANAGEMENT ---
def profile_management():
    st.title("👤 Profile Management")
    user_email = st.session_state.supabase_user.email
    try:
        profiles = supabase.table("profiles").select("*").eq("user_email", user_email).execute()
    except Exception:
        st.error("❌ Failed to fetch profiles. Please try again later.")
        st.stop()

    profile_names = [p["name"] for p in profiles.data] if profiles.data else []
    st.write("Choose a profile or create a new one:")

    selected = st.selectbox("Select Profile", ["Create New"] + profile_names if profile_names else ["Create New"])

    if selected == "Create New":
        new_name = st.text_input("Enter New Profile Name")
        if st.button("Start with New Profile") and new_name:
            if new_name in profile_names:
                st.warning("Profile name already exists. Choose another name.")
            else:
                st.session_state.active_profile = new_name
                st.session_state.step = 0
                st.session_state.profile_selected = True
                st.rerun()
    elif selected:
        st.session_state.active_profile = selected
        st.session_state.step = 0
        st.session_state.profile_selected = True
        profile_data = next((p for p in profiles.data if p["name"] == selected), {})
        st.write(f"**Job Title**: {profile_data.get('job_title', 'N/A')}")
        st.write(f"**QoH Score**: {profile_data.get('qoh_score', 'N/A')}")
        if st.button(f"Edit Profile: {selected}"):
            st.rerun()
        if st.button(f"Delete Profile: {selected}"):
            try:
                supabase.table("profiles").delete().eq("name", selected).eq("user_email", user_email).execute()
                st.success(f"Deleted profile: {selected}")
                st.session_state.profile_selected = False
                st.session_state.active_profile = None
                st.rerun()
            except Exception:
                st.error("Failed to delete profile.")

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
        st.session_state.behavior_score = behavior_score
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        traits = ["Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork",
                  "Adaptability", "Problem Solving", "Empathy", "Initiative", "Collaboration"]

        for i in range(1, 3):
            with st.expander(f"Reference {i}"):
                st.text_input("Name", key=f"ref{i}_name")
                st.text_input("Email", key=f"ref{i}_email")
                st.selectbox("Trait to Highlight", traits, key=f"ref{i}_trait")
                st.text_area("Optional Message", key=f"ref{i}_msg")
                if st.button(f"Send to Ref {i}"):
                    st.success(f"Request sent to {st.session_state.get(f'ref{i}_name')}")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Backchannel (Optional)")
        st.text_input("Name")
        email = st.text_input("Email", key="login_email")
        st.text_area("Message or Topic for Feedback")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Graduation Year")
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

        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire Score")
        jd_scores = st.session_state.get("jd_scores", [75, 80])
        skill_count = len(st.session_state.get("selected_skills", []))
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        qoh, breakdown = calculate_qoh_score(skill_count, ref_score, behavior, jd_scores)
        st.metric("📈 QoH Score", f"{qoh}/100")
        ensure_profile_initialized(st.session_state.active_profile)
        st.session_state.qoh_score = qoh
        st.session_state.profiles[st.session_state.active_profile]["qoh"] = qoh
        st.session_state.profiles[st.session_state.active_profile]["progress"]["Quality of Hire"] = True
        for k, v in breakdown.items():
            st.write(f"**{k}**: {v}/100")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Growth Roadmap")
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
        st.success("🎉 Complete!")

        st.markdown("### 📩 Save Your Profile")
    if st.button("Save My Profile"):
        selected_skills = st.session_state.get("selected_skills", ["Python", "SQL"])
        jd_scores_list = st.session_state.get("jd_scores", [75, 85])
        user_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else "anonymous"
        growth_roadmap = st.session_state.get("growth_roadmap", "• 30-Day: Onboard\n• 60-Day: Deliver small win\n• 90-Day: Lead initiative")
        profile_data = {
            "user_email": user_email,
            "name": st.session_state.get("cand_name", "Demo User"),
            "job_title": st.session_state.get("cand_title", "Demo Role"),
            "resume_text": st.session_state.get("resume_text", "This is a demo resume."),
            "selected_skills": selected_skills,
            "behavior_score": st.session_state.get("behavior_score", 70),
            "reference_data": {"mock": "data"},
            "education": {"mock": "data"},
            "qoh_score": st.session_state.get("qoh_score", 80),
            "jd_scores": jd_scores_list,
            "growth_roadmap": growth_roadmap,
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            result = supabase.table("profiles").insert(profile_data).execute()
            if result.data:
                st.success("✅ Profile saved successfully!")
            else:
                st.error(f"❌ Failed to save profile: {result}")
        except Exception as e:
            st.error(f"❌ Error saving profile: {e}")
            st.error(f"❌ Error saving profile: {e}")


# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")

    with st.sidebar.expander("🎚 Adjust Quality of Hire Weights", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Adjust sliders to see candidate scores.")
        return

    df = pd.DataFrame([
        {
            "Candidate": "Lamont",
            "JD Match": 88,
            "Reference": 90,
            "Behavior": 84,
            "Skill": 92,
            "Gaps": "Strategic Planning",
            "Verified": "✅ Resume, ✅ References, ✅ JD, 🟠 Behavior, ✅ Education, ✅ HR"
        },
        {
            "Candidate": "Jasmine",
            "JD Match": 82,
            "Reference": 78,
            "Behavior": 90,
            "Skill": 80,
            "Gaps": "Leadership",
            "Verified": "✅ Resume, ⚠️ References, ✅ JD, ✅ Behavior, ✅ Education, ❌ HR"
        },
        {
            "Candidate": "Andre",
            "JD Match": 75,
            "Reference": 65,
            "Behavior": 70,
            "Skill": 78,
            "Gaps": "Communication",
            "Verified": "✅ Resume, ❌ References, ✅ JD, ⚠️ Behavior, ❌ Education, ❌ HR"
        }
    ])

    df["QoH Score"] = (
        df["JD Match"] * w_jd +
        df["Reference"] * w_ref +
        df["Behavior"] * w_beh +
        df["Skill"] * w_skill
    ) / total

    df = df.sort_values("QoH Score", ascending=False)
    st.subheader("📊 Candidate Comparison Table")
    st.dataframe(df[["Candidate", "JD Match", "Reference", "Behavior", "Skill", "QoH Score", "Gaps", "Verified"]], use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 AI Recommendations")
    for _, row in df.iterrows():
        score = row["QoH Score"]
        if score >= 90:
            st.success(f"✅ {row['Candidate']}: Strong hire.")
        elif row["Reference"] < 75:
            st.warning(f"⚠️ {row['Candidate']}: Weak reference.")
        elif row["Skill"] < 80:
            st.info(f"ℹ️ {row['Candidate']}: Gap in **{row['Gaps']}**.")
        else:
            st.write(f"{row['Candidate']}: Interview-ready.")


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
        st.header("🔐 Log In or Create Account")
        mode = st.radio("Choose Mode", ["Login", "Sign Up"], key="login_mode")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.session_state.profile_selected = False
                st.success("✅ Logged in successfully.")
                st.rerun()
            except:
                st.error("Login failed. Please check your credentials.")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email.")
            except:
                st.error("Signup failed. Try again with a different email.")

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        if not st.session_state.get("profile_selected"):
            profile_management()
        else:
            candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()

# --- ML VISION DASHBOARD ---
import pandas as pd
import numpy as np

def ml_dashboard():
    st.title("📊 Machine Learning Dashboard (Vision)")

    st.markdown("### 🚀 Data-Driven QoH Refinement")
    st.write("This is a simulation of how more data improves our predictive Quality of Hire (QoH) scoring over time.")

    # Simulated QoH Improvement Over Time
    dates = pd.date_range(start="2024-01-01", periods=12, freq='M')
    qoh_scores = np.linspace(60, 90, 12) + np.random.normal(0, 2, 12)
    df_qoh = pd.DataFrame({"Date": dates, "QoH Score": qoh_scores})
    st.line_chart(df_qoh.set_index("Date"))

    st.markdown("### 📈 Skill Impact Analysis (Simulated)")
    skills = ["Python", "SQL", "Leadership", "Data Analysis", "Communication"]
    impact = [20, 15, 25, 18, 22]
    df_skills = pd.DataFrame({"Skill": skills, "Impact (%)": impact})
    st.bar_chart(df_skills.set_index("Skill"))

    st.markdown("### 🧠 ML Roadmap")
    st.markdown("""
    - **Now**: Static QoH Scoring.
    - **Q2 2024**: Start collecting success data post-hire.
    - **Q3 2024**: Train ML model on historical profiles.
    - **Q4 2024**: Live ML-based QoH Predictions.
    - **2025**: AI-driven hiring assistant, fully adaptive.
    """)

    st.success("🚀 Our system learns and evolves with every profile saved. More data = smarter hiring.")


# --- ROUTING EXTENSION ---
# Add ML Dashboard as a view option
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter", "ML Vision"], key="portal_choice")
    if view == "Candidate":
        if not st.session_state.get("profile_selected"):
            profile_management()
        else:
            candidate_journey()
    elif view == "Recruiter":
        recruiter_dashboard()
    elif view == "ML Vision":
        ml_dashboard()
else:
    login_ui()

# --- UNIFIED ROUTING WITH ML VISION ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter", "ML Vision"], key="portal_choice")
    if view == "Candidate":
        if not st.session_state.get("profile_selected"):
            profile_management()
        else:
            candidate_journey()
    elif view == "Recruiter":
        recruiter_dashboard()
    elif view == "ML Vision":
        ml_dashboard()
else:
    login_ui()
