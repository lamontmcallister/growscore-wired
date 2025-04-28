import streamlit as st
import openai
import pdfplumber
import pandas as pd
import json
from datetime import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="GrowScore Journey", layout="wide")

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
            st.experimental_rerun()
    elif selected:
        st.session_state.active_profile = selected
        st.session_state.step = 0
        if st.button(f"Edit Profile: {selected}"):
            st.experimental_rerun()

# --- EXTENDED CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title(f"🚀 Candidate Journey – Profile: {st.session_state.active_profile}")
    st.progress((step + 1) / 5)

    if step == 0:
        st.markdown("### Step 1: Contact Info")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Target Job Title", key="cand_title")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### Step 2: Skills")
        skills_pool = ["Python", "SQL", "Leadership", "Data Analysis", "Communication"]
        selected = st.multiselect("Choose your strongest skills:", skills_pool)
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### Step 3: Behavioral Survey")
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
        st.markdown("### Step 4: Job Match Simulation")
        jd_scores = [85, 90]  # Placeholder simulated scores
        st.session_state.jd_scores = jd_scores
        st.write("Simulated Job Match Scores:", jd_scores)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### Step 5: Growth Roadmap")
        roadmap = "• 30-Day: Onboard\n• 60-Day: Deliver project\n• 90-Day: Lead initiative\n• 6-Month: Strategic growth\n• 1-Year: Promotion-ready"
        st.markdown(roadmap)
        st.session_state["growth_roadmap_text"] = roadmap
        st.success("🎉 Journey Complete!")

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
                "qoh_score": 85,
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

# --- MAIN ---
def main():
    login_section()
    if st.session_state.get("supabase_user"):
        if "active_profile" not in st.session_state:
            profile_management()
        else:
            candidate_journey()
    else:
        st.warning("Please log in to access GrowScore features.")

if __name__ == "__main__":
    main()
