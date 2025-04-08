
import streamlit as st
from supabase import create_client, Client
import uuid

# -- SETUP --
st.set_page_config(page_title="GrowScore", layout="wide")

# Initialize Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# -- SESSION STATE HANDLING --
if "session" not in st.session_state:
    st.session_state.session = None
if "user" not in st.session_state:
    st.session_state.user = None
if "profile_created" not in st.session_state:
    st.session_state.profile_created = False
if "view" not in st.session_state:
    st.session_state.view = "login"

# -- AUTH LOGIC --
def login_user(email, password):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.session = result.session
        st.session_state.user = result.user
        st.session_state.view = "candidate_journey"
    except Exception as e:
        st.error(f"Login failed: {e}")

def signup_user(email, password):
    try:
        result = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Sign up successful. Please check your email to confirm.")
    except Exception as e:
        st.error(f"Sign up failed: {e}")

def logout_user():
    supabase.auth.sign_out()
    st.session_state.clear()

# -- LOGIN / SIGNUP UI --
def login_ui():
    st.title("🔐 Welcome to GrowScore")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            login_user(email, password)
    with tab2:
        email = st.text_input("New Email", key="signup_email")
        password = st.text_input("New Password", type="password", key="signup_password")
        if st.button("Sign Up"):
            signup_user(email, password)

# -- CANDIDATE JOURNEY UI --
def candidate_journey():
    st.title("🚀 Candidate Journey")

    with st.form("profile_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        job_title = st.text_input("Current Job Title")
        submitted = st.form_submit_button("Save Profile")

        if submitted:
            user_id = st.session_state.user.id
            payload = {
                "user_id": user_id,
                "full_name": full_name,
                "email": email,
                "job_title": job_title
            }
            try:
                supabase.table("profiles").insert(payload).execute()
                st.success("✅ Profile saved successfully!")
                st.session_state.profile_created = True
            except Exception as e:
                st.error(f"❌ Error saving profile: {e}")

    if st.session_state.profile_created:
        st.markdown("✅ Continue to Resume & Skills section...")

# -- RECRUITER DASHBOARD UI --
def recruiter_dashboard():
    st.title("📊 Recruiter Dashboard")
    try:
        result = supabase.table("profiles").select("*").execute()
        rows = result.data
        if rows:
            st.dataframe(rows)
        else:
            st.info("No candidate profiles found.")
    except Exception as e:
        st.error(f"Error loading profiles: {e}")

# -- ROUTING --
with st.sidebar:
    if st.session_state.user:
        st.success(f"Logged in as {st.session_state.user.email}")
        if st.button("🔄 Logout"):
            logout_user()
    else:
        st.info("Please log in or sign up")

    view = st.radio("View", ["Candidate Journey", "Recruiter Dashboard"])
    if view == "Candidate Journey":
        st.session_state.view = "candidate_journey"
    else:
        st.session_state.view = "recruiter_dashboard"

if st.session_state.view == "login":
    login_ui()
elif st.session_state.view == "candidate_journey":
    candidate_journey()
elif st.session_state.view == "recruiter_dashboard":
    recruiter_dashboard()
