
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title='Skippr Login Test', layout='wide')

# Load secrets
SUPABASE_URL = st.secrets['supabase']['url']
SUPABASE_KEY = st.secrets['supabase']['key']

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Session state
if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "show_app" not in st.session_state:
    st.session_state.show_app = False
if "is_signup" not in st.session_state:
    st.session_state.is_signup = False

# Auth logic
def handle_auth(email, password):
    try:
        if st.session_state.is_signup:
            result = supabase.auth.sign_up({"email": email, "password": password})
        else:
            result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if result and result.user:
            st.session_state.supabase_user = result.user
            st.session_state.supabase_session = result.session
            st.session_state.show_app = True
        else:
            st.error("Authentication failed.")
    except Exception as e:
        st.error(f"Auth error: {e}")

# Login UI
if not st.session_state.show_app:
    with st.sidebar:
        st.title("🚪 Login to Skippr")
        st.write("Sign in or sign up to continue.")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        st.session_state.is_signup = st.checkbox("New user? Sign up", key="signup_toggle")
        if st.button("Continue", key="auth_continue"):
            handle_auth(email, password)
    st.stop()

# Placeholder success content
st.success("✅ Logged in! Welcome to Skippr.")
