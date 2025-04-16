import streamlit as st
import streamlit_authenticator as stauth
from pathlib import Path
import yaml
from yaml.loader import SafeLoader

# Load custom CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Sidebar stays for layout or additional features later
with st.sidebar:
    st.title("🔐 Login")

    # Load authentication config
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

    name, authentication_status, username = authenticator.login("Login", "main")

# Hero / Mission Section - Centered Content
st.markdown("""
<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh; text-align: center;'>
    <h1>🚪 Backdoor – Unlocking Hidden Career Opportunities</h1>
    <h3>Redefining the Hiring Process with AI-Driven Insights</h3>
    <br>
    <a href='#' style='text-decoration: none;'>
        <button style='margin-top: 20px;'>🚀 Skip</button>
    </a>
</div>
""", unsafe_allow_html=True)

# Authenticated content goes here if login successful
if authentication_status:
    st.success(f"Welcome back, {name}!")
    # Add your logged-in logic here
elif authentication_status is False:
    st.error("Username/password is incorrect.")
elif authentication_status is None:
    st.info("Please enter your username and password.")
