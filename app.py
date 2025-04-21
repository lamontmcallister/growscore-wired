import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client, Client
from uuid import uuid4

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

# --- SESSION ---
for k in ["supabase_session", "supabase_user", "step", "profile_id", "profile_name"]:
    if k not in st.session_state:
        st.session_state[k] = None if k not in ["step"] else 0

skills_pool = ["Python", "SQL", "Leadership", "Communication", "Data Analysis", "Machine Learning", "Excel", "Strategy", "Project Management"]

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

# --- PROFILE UTILS ---
def get_profiles(user_id):
    try:
        res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        return res.data
    except:
        return []

def save_profile(user_id, profile_id, name, data):
    try:
        supabase.table("profiles").upsert({
            "id": profile_id,
            "user_id": user_id,
            "name": name,
            "data": data,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        st.error(f"❌ Error saving profile: {e}")

# --- LOGIN ---
def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=350)
        st.markdown("### From Rejection to Revolution")
        st.caption("💡 I didn’t get the job. I built the platform that fixes the problem.")

    st.markdown("---")

    with st.sidebar:
        st.header("🔐 Log In or Sign Up")
        mode = st.radio("Choose Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check your email.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# --- PROFILE SELECTOR ---
def profile_selector():
    st.subheader("👤 Candidate Profiles")
    user_id = st.session_state.supabase_user["id"]
    profiles = get_profiles(user_id)

    options = [p["name"] for p in profiles]
    options.append("➕ Create New Profile")

    selected = st.selectbox("Choose a profile to continue:", options)

    if selected == "➕ Create New Profile":
        name = st.text_input("Name your new profile")
        if st.button("Start New Profile") and name:
            new_id = str(uuid4())
            st.session_state.profile_id = new_id
            st.session_state.profile_name = name
            st.session_state.step = 0
    else:
        for p in profiles:
            if p["name"] == selected:
                st.session_state.profile_id = p["id"]
                st.session_state.profile_name = p["name"]
                st.session_state.step = 0
                break
# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title(f"🚀 Candidate Journey – {st.session_state.profile_name}")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Info")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state["resume_contact"] = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Skills")
        selected = st.multiselect("Select top skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.caption("Choose how you respond in the workplace.")
        questions = {
            "Meets deadlines consistently": None,
            "Collaborates well in teams": None,
            "Adapts quickly to change": None,
            "Demonstrates leadership": None,
            "Communicates effectively": None,
        }
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        total = 0
        for i, q in enumerate(questions):
            r = st.radio(q, opts, index=2, key=f"behav_{i}")
            total += score_map[r]
        st.session_state.behavior_score = round((total / (len(questions) * 5)) * 100, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        traits = ["Leadership", "Communication", "Reliability", "Teamwork", "Problem Solving"]
        for i in range(1, 3):
            with st.expander(f"Reference {i}"):
                st.text_input("Name", key=f"ref{i}_name")
                st.text_input("Email", key=f"ref{i}_email")
                st.selectbox("Trait to Highlight", traits, key=f"ref{i}_trait")
                st.text_area("Message", key=f"ref{i}_msg")
                if st.button(f"Send to Ref {i}"):
                    st.success(f"Reference {i} sent.")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Backchannel (Optional)")
        st.text_input("Name")
        st.text_input("Email")
        st.text_area("Message")
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
        st.markdown("### 🏢 Step 7: HR Verification")
        st.text_input("Most Recent Company")
        st.text_input("Manager's Name")
        st.text_input("HR Contact Email")
        st.checkbox("I authorize verification")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: JD Matching")
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
        jd_scores = st.session_state.get("jd_scores", [75, 85])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        qoh = round((skills + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Growth Roadmap")
        resume = st.session_state.get("resume_text", "")
        prompt = f"Create a roadmap from this resume:\n{resume}\n\nInclude:\n- 30 day\n- 60 day\n- 90 day\n- 6 month\n- 1 year goals"
        try:
            res = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = res.choices[0].message.content.strip()
        except:
            roadmap = "• 30d: Learn systems\n• 60d: Lead project\n• 90d: Present results\n• 6mo: Mentorship\n• 1y: Promotion"
        st.markdown(f"**📍 Your Roadmap:**\n\n{roadmap}")
        st.success("🎉 Profile complete!")

        if st.session_state.profile_id:
            save_profile(
                user_id=st.session_state.supabase_user["id"],
                profile_id=st.session_state.profile_id,
                name=st.session_state.profile_name,
                data={"qoh": st.session_state.qoh_score}
            )

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚 QoH Weights", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)
    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Set weights to begin.")
        return
    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Reference": 90, "Behavior": 84, "Skill": 92, "Gaps": "Strategic Thinking"},
        {"Candidate": "Jasmine", "JD Match": 82, "Reference": 78, "Behavior": 90, "Skill": 80, "Gaps": "Leadership"},
        {"Candidate": "Andre", "JD Match": 75, "Reference": 65, "Behavior": 70, "Skill": 78, "Gaps": "Communication"}
    ])
    df["QoH Score"] = (
        df["JD Match"] * w_jd + df["Reference"] * w_ref + df["Behavior"] * w_beh + df["Skill"] * w_skill
    ) / total
    df = df.sort_values("QoH Score", ascending=False)
    st.dataframe(df[["Candidate", "JD Match", "Reference", "Behavior", "Skill", "QoH Score", "Gaps"]], use_container_width=True)
    st.markdown("### 🔍 AI Insights")
    for _, row in df.iterrows():
        score = row["QoH Score"]
        if score >= 90:
            st.success(f"{row['Candidate']}: 🌟 Top-tier candidate.")
        elif row["Reference"] < 75:
            st.warning(f"{row['Candidate']}: ⚠️ Weak reference, follow up needed.")
        else:
            st.info(f"{row['Candidate']}: Good fit. Ready for next steps.")

# --- ROUTING ---
if st.session_state.supabase_user:
    if not st.session_state.profile_id:
        profile_selector()
    elif st.session_state.profile_id:
        view = st.sidebar.radio("Portal", ["Candidate", "Recruiter"])
        if view == "Candidate":
            candidate_journey()
        else:
            recruiter_dashboard()
else:
    login_ui()
