import streamlit as st
import openai
import pdfplumber
import pandas as pd
import ast
import json
from datetime import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="GrowScore Full", layout="wide")

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
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Login error: {e}")
    if st.session_state.get("supabase_user"):
        if st.sidebar.button("Log Out"):
            st.session_state.supabase_user = None
            st.rerun()

# --- PROFILE MANAGEMENT ---
def profile_management():
    st.title("👤 Profile Management")
    user_email = st.session_state.supabase_user.user.email
    try:
        profiles = supabase.table("profiles").select("*").eq("user_email", user_email).execute()
    except Exception as e:
        st.error(f"❌ Supabase query error: {e}")
        st.stop()

    profile_names = [p["name"] for p in profiles.data] if profiles.data else []
    st.write("Choose a profile or create a new one:")
    if profile_names:
        selected = st.selectbox("Select Existing Profile", ["Create New"] + profile_names)
    else:
        selected = "Create New"
        st.info("No profiles found. Create a new one.")
    if selected == "Create New":
        new_name = st.text_input("Enter New Profile Name")
        if st.button("Start with New Profile") and new_name:
            st.session_state.active_profile = new_name
            st.session_state.step = 0
            st.rerun()
    elif selected:
        st.session_state.active_profile = selected
        st.session_state.step = 0
        if st.button(f"Edit Profile: {selected}"):
            st.rerun()

# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)

    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title(f"🚀 Candidate Journey – Profile: {st.session_state.active_profile}")
    st.progress((step + 1) / 8)

    if step == 0:
        st.markdown("### Step 1: Contact Info + Resume Upload")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### Step 2: Skills + Behavior Survey")
        skills_pool = ["Python", "SQL", "Leadership", "Data Analysis", "Communication"]
        selected = st.multiselect("Choose your strongest skills:", skills_pool)
        st.session_state.selected_skills = selected

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

    elif step == 2:
        st.markdown("### Step 3: References")
        st.text_input("Reference 1 Name", key="ref1_name")
        st.text_input("Reference 1 Email", key="ref1_email")
        st.text_input("Reference 2 Name", key="ref2_name")
        st.text_input("Reference 2 Email", key="ref2_email")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### Step 4: Education")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Grad Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### Step 5: Job Match Scoring")
        jd1 = st.text_area("Paste Job Description 1")
        jd2 = st.text_area("Paste Job Description 2")
        if jd1 and "resume_text" in st.session_state:
            jd_scores = [85, 90]  # Simulated scores
            st.session_state.jd_scores = jd_scores
            for i, score in enumerate(jd_scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### Step 6: Quality of Hire (QoH) Score")
        jd_scores = st.session_state.get("jd_scores", [75, 80])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        qoh = round((skills + behavior + ref_score + avg_jd) / 4, 1)
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### Step 7: Growth Roadmap")
        roadmap = "• 30-Day: Onboard\n• 60-Day: Deliver project\n• 90-Day: Lead initiative\n• 6-Month: Strategic growth\n• 1-Year: Promotion-ready"
        st.markdown(roadmap)
        st.session_state["growth_roadmap_text"] = roadmap
        st.success("🎉 Journey Complete!")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📩 Save Your Profile")
        if st.button("Save My Profile"):
            user_email = st.session_state.supabase_user.user.email
            profile_data = {
                "user_email": user_email,
                "name": st.session_state.active_profile,
                "job_title": st.session_state.get("cand_title", ""),
                "selected_skills": st.session_state.get("selected_skills", []),
                "behavior_score": st.session_state.get("behavior_score", 0),
                "reference_data": json.dumps({"mock": "data"}),
                "education": json.dumps({"mock": "data"}),
                "qoh_score": st.session_state.get("qoh_score", 0),
                "jd_scores": st.session_state.get("jd_scores", []),
                "growth_roadmap": st.session_state.get("growth_roadmap_text", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            try:
                existing = supabase.table("profiles").select("*").eq("user_email", user_email).eq("name", st.session_state.active_profile).execute()
                if existing.data:
                    supabase.table("profiles").update(profile_data).eq("user_email", user_email).eq("name", st.session_state.active_profile).execute()
                    st.success("✅ Profile updated!")
                else:
                    supabase.table("profiles").insert(profile_data).execute()
                    st.success("✅ Profile saved!")
            except Exception as e:
                st.error(f"❌ Error saving profile: {e}")
        st.button("Back", on_click=prev_step)


# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚 Customize QoH Weights", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total_weight = max(1, w_jd + w_ref + w_beh + w_skill)

    try:
        profiles = supabase.table("profiles").select("*").execute()
        data = profiles.data if profiles.data else []
    except Exception as e:
        st.error(f"❌ Could not fetch profiles: {e}")
        return

    if data:
        df = pd.DataFrame(data)
        df["skills_score"] = df["selected_skills"].apply(lambda x: len(x) * 5 if isinstance(x, list) else 0)
        df["avg_jd"] = df["jd_scores"].apply(lambda x: sum(x)/len(x) if isinstance(x, list) and len(x) > 0 else 0)
        df["QoH"] = (
            df["avg_jd"] * w_jd +
            df["skills_score"] * w_skill +
            df["behavior_score"] * w_beh +
            90 * w_ref
        ) / total_weight
        df = df.sort_values("QoH", ascending=False)

        st.metric("📊 Average QoH", f"{df['QoH'].mean():.1f}/100")
        st.dataframe(df[["name", "job_title", "avg_jd", "skills_score", "behavior_score", "QoH"]])
    else:
        st.info("No profiles found.")

# --- MAIN ---
def main():
    login_section()
    if st.session_state.get("supabase_user"):
        mode = st.sidebar.selectbox("Mode", ["Candidate", "Recruiter"])
        if mode == "Candidate":
            if "active_profile" not in st.session_state:
                profile_management()
            else:
                candidate_journey()
        elif mode == "Recruiter":
            recruiter_dashboard()
    else:
        st.warning("Please log in to access GrowScore features.")

if __name__ == "__main__":
    main()
