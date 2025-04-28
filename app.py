import streamlit as st
import openai
import pdfplumber
import pandas as pd
import ast
import json
from datetime import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="GrowScore Polished", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- AUTH WITH LOGO ---
def login_section():
    st.sidebar.image("YOUR_LOGO_IMAGE_PATH.PNG", use_column_width=True)  # Replace with correct path
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

# --- PROFILE MANAGEMENT (UNCHANGED) ---
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

# --- POLISHED CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)

    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.header(f"🚀 Candidate Journey – Profile: {st.session_state.active_profile}")
    st.progress((step + 1) / 8)

    if step == 2:
        st.subheader("🤝 Step 3: References")
        for idx in range(1, 3):
            st.text_input(f"Reference {idx} Name", key=f"ref{idx}_name")
            st.text_input(f"Reference {idx} Email", key=f"ref{idx}_email")
            st.selectbox(f"Trait for Ref {idx}", ["Leadership", "Communication", "Teamwork"], key=f"ref{idx}_trait")
        st.text_area("Backchannel Notes (Private)", key="backchannel_notes")
        st.button("⬅️ Back", on_click=prev_step)
        st.button("Next ➡️", on_click=next_step)

    # Continue remaining steps...

# --- RECRUITER DASHBOARD ENHANCED ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    show_verified = st.checkbox("Show Only Verified Candidates", value=False)

    try:
        profiles = supabase.table("profiles").select("*").execute()
        data = profiles.data if profiles.data else []
    except Exception as e:
        st.error(f"❌ Could not fetch profiles: {e}")
        return

    if data:
        df = pd.DataFrame(data)
        df["Verified"] = df.get("verified", False)
        if show_verified:
            df = df[df["Verified"] == True]

        for idx, row in df.iterrows():
            st.subheader(f"{row['name']} – {row['job_title']}")
            st.text(f"QoH: {row['qoh_score']} / Behavior: {row['behavior_score']} / JD Avg: {row['jd_scores']}")
            st.text(f"Verified: {'✅' if row['Verified'] else '❌'}")
            st.text(f"Backchannel Note: {row.get('backchannel_notes', 'None')}")

            if st.button(f"Toggle Verification – {row['name']}", key=f"verify_{idx}"):
                new_status = not row["Verified"]
                supabase.table("profiles").update({"verified": new_status}).eq("name", row["name"]).execute()
                st.experimental_rerun()
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
