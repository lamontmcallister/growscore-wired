import streamlit as st
import ast
import json
import pdfplumber
import pandas as pd
from supabase import Client
from datetime import datetime
from db.client import get_supabase_client
from ai.client import get_openai_client
from ai.resume import call_openai_json, extract_skills_from_resume, extract_contact_info, match_resume_to_jds
from auth.roles import get_user_role

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")

supabase: Client = get_supabase_client()
openai_client = get_openai_client()

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

def calculate_qoh_score(skill_count, ref, behav, jd_scores):
    if not jd_scores:
        return None, None
    avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
    skills = min(skill_count * 5, 100)
    final = round((skills + ref + behav + avg_jd) / 4, 1)
    return final, {"Skills": skills, "References": ref, "Behavior": behav, "JD Match": avg_jd}


# --- PROFILE MANAGEMENT ---
def profile_management():
    st.title("👤 Profile Management")
    user_email = st.session_state.supabase_user.email
    try:
        profiles = supabase.table("profiles").select("*").eq("user_email", user_email).execute()
    except Exception as e:
        st.error(f"❌ Failed to fetch profiles: {e}")
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
                profile_data = {
                    "user_email": user_email,
                    "name": new_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    supabase.table("profiles").insert(profile_data).execute()
                    st.success(f"✅ New profile '{new_name}' created successfully!")
                    st.session_state.active_profile = new_name
                    st.session_state.step = 0
                    st.session_state.profile_selected = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating profile: {e}")
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
            except Exception as e:
                st.error(f"Failed to delete profile: {e}")


# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Contact Info")
        st.markdown("""_We'll use your resume to extract relevant skills and auto-fill your contact info. You control what gets shared._""")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text

            with st.spinner("Extracting skills..."):
                skills, skills_error = extract_skills_from_resume(text)
            if skills_error:
                st.warning(f"⚠️ Couldn't auto-extract skills ({skills_error}). You can still select them manually below.")
                st.session_state.resume_skills = []
            else:
                st.session_state.resume_skills = skills

            with st.spinner("Extracting contact info..."):
                contact, contact_error = extract_contact_info(text)
            if contact_error:
                st.warning(f"⚠️ Couldn't auto-extract contact info ({contact_error}). Please fill it in manually above.")
            else:
                st.session_state.resume_contact = contact

            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        st.markdown("""_These skills help recruiters understand your strengths. Adjust or add based on what best represents you._""")
        resume_skills = st.session_state.get("resume_skills", [])
        # Build the options list from the fixed pool PLUS whatever the AI
        # extracted from this resume, so multiselect's default never
        # references a value that isn't in its own options (Streamlit
        # raises StreamlitAPIException if that happens).
        available_skills = list(dict.fromkeys(skills_pool + resume_skills))
        selected = st.multiselect("Choose your strongest skills:", available_skills, default=resume_skills)
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.markdown("""_This survey helps highlight how you work. It's part of your Quality of Hire score._""")
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
        st.markdown("""_References build credibility. These are private and only used to strengthen your application._""")
        traits = ["Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork", "Adaptability", "Problem Solving", "Empathy", "Initiative", "Collaboration"]
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
        st.markdown("""_Backchannel input gives you insights into teams or companies from people who've worked there._""")
        st.text_input("Name")
        st.text_input("Email")
        st.text_area("Message or Topic for Feedback")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education")
        st.markdown("""_Add education details to boost trust and completeness in your profile._""")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Graduation Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 🏢 Step 7: HR Check")
        st.markdown("""_You can request verification from past employers here. It's a future feature — no emails will be sent now._""")
        st.text_input("Company")
        st.text_input("Manager")
        st.text_input("HR Email")
        st.checkbox("I authorize verification")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: Job Matching")
        st.markdown("""_We'll compare your resume to real job descriptions to highlight your fit and readiness._""")
        jd1 = st.text_area("Paste JD 1")
        jd2 = st.text_area("Paste JD 2")
        if jd1 and "resume_text" in st.session_state:
            with st.spinner("Matching against job descriptions..."):
                scores, match_error = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            if match_error:
                st.error(f"⚠️ Couldn't compute JD match scores right now ({match_error}). Try again in a moment.")
                st.session_state.jd_scores = []
            else:
                st.session_state.jd_scores = scores
                for i, score in enumerate(scores):
                    st.markdown(f"**JD {i+1} Match Score:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire Score")
        st.markdown("""_This is your full Quality of Hire score — built from your skills, behavior, references, and JD match._""")
        jd_scores = st.session_state.get("jd_scores", [])
        skill_count = len(st.session_state.get("selected_skills", []))
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        qoh, breakdown = calculate_qoh_score(skill_count, ref_score, behavior, jd_scores)
        if qoh is None:
            st.warning("⚠️ No JD match scores yet — go back to Step 8 and paste a job description first.")
        else:
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
        st.markdown("""_This personalized roadmap gives you ideas for 30/60/90-day growth, learning, and next steps._""")
        prompt = (
            f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\n"
            'Create a career roadmap. Respond as JSON: '
            '{"30_day": "...", "60_day": "...", "90_day": "...", "6_month": "...", "1_year": "..."}'
        )
        roadmap_data, roadmap_error = call_openai_json(prompt, temperature=0.7)
        if roadmap_error:
            st.error(f"⚠️ Couldn't generate a roadmap right now ({roadmap_error}). You can still save your profile below.")
            roadmap = None
        else:
            roadmap = roadmap_data
            st.markdown(f"**30-Day:** {roadmap.get('30_day', '')}")
            st.markdown(f"**60-Day:** {roadmap.get('60_day', '')}")
            st.markdown(f"**90-Day:** {roadmap.get('90_day', '')}")
            st.markdown(f"**6-Month:** {roadmap.get('6_month', '')}")
            st.markdown(f"**1-Year:** {roadmap.get('1_year', '')}")
            st.success("🎉 Complete!")

        st.markdown("### 📩 Save Your Profile")
        if st.button("Save My Profile"):
            selected_skills = st.session_state.get("selected_skills", [])
            jd_scores_list = st.session_state.get("jd_scores", [])
            user_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else None
            if not user_email:
                st.error("❌ You must be logged in to save a profile.")
            else:
                profile_data = {
                    "user_email": user_email,
                    "name": st.session_state.get("active_profile"),
                    "job_title": st.session_state.get("cand_title", ""),
                    "resume_text": st.session_state.get("resume_text", ""),
                    "selected_skills": selected_skills,
                    "behavior_score": st.session_state.get("behavior_score"),
                    "reference_data": {"mock": "data"},  # TODO: wire real reference data once Step 4 persists it
                    "education": {"mock": "data"},        # TODO: wire real education data once Step 6 persists it
                    "qoh_score": st.session_state.get("qoh_score"),
                    "jd_scores": jd_scores_list,
                    "growth_roadmap": roadmap,
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    result = supabase.table("profiles").update(profile_data) \
                        .eq("user_email", user_email) \
                        .eq("name", profile_data["name"]).execute()
                    if result.data:
                        st.success("✅ Profile updated successfully!")
                    else:
                        supabase.table("profiles").insert(profile_data).execute()
                        st.success("✅ Profile created successfully!")
                    st.session_state.profile_saved = True
                except Exception as e:
                    st.error(f"❌ Error saving profile: {e}")

        if st.session_state.get("profile_saved"):
            if st.button("🏠 Home"):
                st.session_state.step = 0
                st.session_state.profile_selected = False
                st.session_state.profile_saved = False
                st.rerun()


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

    try:
        result = supabase.table("profiles").select("*").execute()
    except Exception as e:
        st.error(f"❌ Failed to load candidates: {e}")
        return

    rows = result.data or []
    if not rows:
        st.info("No candidate profiles have been submitted yet.")
        return

    def jd_match(row):
        scores = row.get("jd_scores") or []
        return round(sum(scores) / len(scores), 1) if scores else None

    def skill_score(row):
        skills = row.get("selected_skills") or []
        return min(len(skills) * 10, 100)

    records = []
    for row in rows:
        jd = jd_match(row)
        behavior = row.get("behavior_score")
        skill = skill_score(row)
        if jd is None or behavior is None:
            records.append({
                "Candidate": row.get("name", "Unknown"),
                "JD Match": jd if jd is not None else "—",
                "Behavior": behavior if behavior is not None else "—",
                "Skill": skill,
                "QoH Score": "Incomplete",
                "Gaps": "Missing JD match and/or behavioral survey data",
            })
            continue
        records.append({
            "Candidate": row.get("name", "Unknown"),
            "JD Match": jd,
            "Behavior": behavior,
            "Skill": skill,
            "QoH Score": round((jd * w_jd + behavior * w_beh + skill * w_skill) / (w_jd + w_beh + w_skill), 1) if (w_jd + w_beh + w_skill) else "—",
            "Gaps": "",
        })

    df = pd.DataFrame(records)
    st.subheader("📊 Candidate Comparison Table")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 AI Recommendations")
    for _, row in df.iterrows():
        score = row["QoH Score"]
        if score == "Incomplete":
            st.info(f"ℹ️ {row['Candidate']}: {row['Gaps']}")
        elif score >= 90:
            st.success(f"✅ {row['Candidate']}: Strong hire.")
        elif row["Behavior"] < 70:
            st.warning(f"⚠️ {row['Candidate']}: Weak behavioral signal.")
        elif row["Skill"] < 50:
            st.info(f"ℹ️ {row['Candidate']}: Thin skill coverage.")
        else:
            st.write(f"{row['Candidate']}: Interview-ready.")


# --- LOGIN UI ---
def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=350)
        st.markdown("### From Rejection to Revolution")
        st.caption("💡 I didn't get the job. I built the platform that fixes the problem.")

    st.markdown("---")

    with st.sidebar:
        st.header("🔐 Log In or Create Account")
        mode = st.radio("Choose Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.session_state.profile_selected = False
                st.success("✅ Logged in successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# --- ROUTING ---
# NOTE: manual portal switch for local testing. This bypasses the
# server-side role check in auth/roles.py -- do not ship this to real
# users without bringing back get_user_role() as the actual gate.
if st.session_state.supabase_user:
    with st.sidebar:
        st.markdown("---")
        portal = st.radio("View As (testing only)", ["Candidate", "Recruiter"], key="portal_choice")

    if portal == "Recruiter":
        recruiter_dashboard()
    else:
        if not st.session_state.get("profile_selected"):
            profile_management()
        else:
            candidate_journey()
else:
    login_ui()
